# Recommendation Engine Design

## Overview
The Recommendation Engine is a core component designed to personalize the user experience by suggesting relevant products based on user behavior, historical data, and product attributes.

Current implementation note:

- ML-grade recommendation ranking is still future work in this repository.
- The architecture in this document remains a target-state design and is not part of the currently implemented backend feature set.

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
  "success": true,
  "data": {
    "strategy": "hybrid_personalization",
    "recommendations": [
      {
        "id": "prod_123",
        "name": "Wireless Headphones",
        "score": 0.95,
        "reason": "Based on your recent search for 'audio'"
      },
      ...
    ]
  }
}
```

#### Track Interaction
`POST /api/v1/recommendations/events`

**Payload:**
```json
{
  "eventType": "view",
  "productId": "prod_123",
  "metadata": {
    "duration": 5,
    "source": "search_results"
  }
}
```
