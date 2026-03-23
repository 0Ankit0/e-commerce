# Recommendation Engine Design

## Overview
The Recommendation Engine is a core component designed to personalize the user experience by suggesting relevant products based on user behavior, historical data, and product attributes.

Current implementation note:

- The backend now exposes an implemented hybrid ranker under `GET /api/v1/recommendations` and event ingestion under `POST /api/v1/recommendations/events`.
- The full streaming feature-store architecture in this document is still a target-state evolution, not a hard dependency of the current repository.

## Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        UserEvents[User Events<br>(Views, Clicks)]
        OrderHistory[Order History]
        CartData[Cart Data]
        ProductMetadata[Product Metadata]
    end

    subgraph "Processing Layer"
        StreamProcessor[Stream Processor<br>Kafka + Flink/Spark]
        BatchProcessor[Batch Processor<br>Airflow + Spark]
    end

    subgraph "Storage Layer"
        FeatureStore[(Feature Store<br>Redis/Cassandra)]
        ModelStore[(Model Store<br>S3)]
        VectorDB[(Vector DB<br>Milvus/Pinecone)]
    end

    subgraph "Serving Layer"
        RecService[Recommendation Service]
        ABTesting[A/B Testing]
    end

    UserEvents --> StreamProcessor
    OrderHistory --> BatchProcessor
    CartData --> StreamProcessor
    ProductMetadata --> BatchProcessor

    StreamProcessor --> FeatureStore
    BatchProcessor --> FeatureStore
    BatchProcessor --> VectorDB

    FeatureStore --> RecService
    VectorDB --> RecService
    ModelStore --> RecService

    RecService --> Client[Client App]
```

## Algorithms & Strategies

### 1. Collaborative Filtering (User-User & Item-Item)
- **Input**: User purchase history, ratings, and view logs.
- **Logic**: Users who bought X also bought Y.
- **Use Case**: "Customers who viewed this item also viewed".

### 2. Content-Based Filtering
- **Input**: Product attributes (category, brand, price, tags) and user preferences.
- **Logic**: Recommend products similar to those the user has liked/bought.
- **Use Case**: "Similar products" on product detail page.

### 3. Real-time Personalization
- **Input**: Current session data (cart items, recent views).
- **Logic**: Context-aware recommendations based on immediate intent.
- **Use Case**: "Recommended for you" on homepage, "Complete your look" in cart.

### 4. Hybrid Approach
- Combines the above methods using a weighted ensemble model to improve accuracy and handle cold-start problems.

## Data Factors
The recommendation score is calculated based on a weighted sum of the following factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Cart Contents** | High | Items currently in cart indicate strong intent. |
| **Order History** | Medium | Past purchases reveal long-term preferences. |
| **Product Views** | Medium | Recent interest in specific items or categories. |
| **Search Queries** | High | Explicit expression of current capability/need. |
| **Similar Users** | Low | Trends from users with similar behavior profiles. |
| **Trending/Popular** | Low | Fallback for cold-start or discovery. |

## Current Repository Implementation

The running backend uses a weighted ranker with persisted recommendation events and re-ranking logic:

- Popularity features from views, cart adds, wishlist adds, purchases, and aggregate popularity score
- Bayesian rating smoothing from `avg_rating` and `review_count`
- Recency decay from product creation time
- Stock-aware scoring so unavailable items are filtered and low-stock items are downweighted
- User category and brand affinities learned from prior events and completed orders
- Context-product similarity and category/brand match for product-detail placements
- Price-fit scoring from the shopper's observed order price profile
- Diversity re-ranking to reduce repeated categories and brands in the final list
- Human-readable recommendation reasons derived from the strongest feature contribution

## API Design

### Endpoints

#### Get Recommendations
`GET /api/v1/recommendations`

**Query Parameters:**
- `type`: `home`, `product_detail`, `cart`, `search`
- `productId`: (Optional) Context product ID for similarity.
- `limit`: Number of items (default 10).

**Response:**
```json
{
  "strategy": "ml_ranker_v2",
  "items": [
    {
      "id": "Aa7r1Gxm",
      "name": "Wireless Headphones",
      "score": 7.12,
      "reason": "Based on your recent shopping signals",
      "ranking_features": {
        "popularity": 0.81,
        "rating": 0.78,
        "recency": 0.93,
        "stock": 1.0,
        "category_affinity": 0.88
      }
    }
  ]
}
```

#### Track Interaction
`POST /api/v1/recommendations/events`

**Payload:**
```json
{
  "event_type": "view",
  "product_id": "Aa7r1Gxm",
  "metadata": {
    "duration": 5,
    "source": "search_results"
  }
}
```
