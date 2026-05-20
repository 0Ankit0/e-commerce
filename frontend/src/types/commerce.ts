export interface CatalogCategory {
  id: string;
  parent_id?: string | null;
  name: string;
  slug: string;
  level: number;
  description: string;
  sort_order?: number;
  attributes: CategoryAttributeSchema[];
  updated_at?: string;
}

export interface CategoryAttributeSchema {
  name: string;
  type: 'text' | 'number' | 'boolean' | 'select';
  required: boolean;
  options?: string[];
  description: string;
}

export interface CatalogBrand {
  id: string;
  name: string;
  slug: string;
  description: string;
}

export interface CatalogProductImage {
  id: string;
  url: string;
  thumbnail_url: string;
  alt_text: string;
  position: number;
  is_primary: boolean;
}

export interface CatalogVariant {
  id: string;
  sku: string;
  name: string;
  mrp: number;
  selling_price: number;
  attributes: Record<string, unknown>;
  available_qty: number;
  is_default: boolean;
  is_active: boolean;
}

export interface CatalogProduct {
  id: string;
  vendor_id: string;
  category: {
    id: string;
    name: string;
    slug: string;
  } | null;
  brand: {
    id: string;
    name: string;
    slug: string;
  } | null;
  name: string;
  slug: string;
  short_description: string;
  description: string;
  specifications: Record<string, unknown>;
  status: string;
  avg_rating: number;
  review_count: number;
  view_count: number;
  is_featured: boolean;
  images: CatalogProductImage[];
  variants: CatalogVariant[];
  min_selling_price: number | null;
  in_stock: boolean;
  created_at: string;
}

export interface CatalogListResponse<T> {
  items: T[];
  total: number;
  page?: number;
  limit?: number;
}

export interface ProductDetailResponse {
  product: CatalogProduct;
}

export interface CatalogBanner {
  id: string;
  title: string;
  subtitle: string;
  image_url: string;
  cta_label: string;
  cta_url: string;
  placement: string;
}

export interface CartItem {
  id: string;
  variant_id: string;
  product_id: string | null;
  product_name: string;
  variant_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  available_qty: number;
}

export interface Cart {
  id: string;
  coupon_id: string | null;
  coupon_code: string | null;
  items: CartItem[];
  subtotal: number;
  discount: number;
  total: number;
}

export interface Address {
  id: string;
  name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
  landmark: string;
  type: string;
  is_default: boolean;
}

export interface AddressSuggestion {
  source: string;
  label: string;
  city: string;
  state: string;
  country: string;
  pincode: string;
  line1: string;
  line2: string;
  latitude?: string;
  longitude?: string;
  place_id?: string;
}

export interface WishlistItem {
  id: string;
  product_id: string;
  name: string;
  slug: string;
  status: string;
  image_url: string;
  price: number | null;
  variant_id: string | null;
  variant_name: string;
}

export interface WishlistShareLink {
  id: string;
  token: string;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SharedWishlistResponse {
  share_link: WishlistShareLink;
  owner: {
    username: string;
  };
  items: WishlistItem[];
  total: number;
}

export interface ShippingQuote {
  serviceable: boolean;
  zone_code: string | null;
  shipping_rate: number;
  cod_enabled: boolean;
  shipping_option: string | null;
}

export interface CheckoutQuote {
  cart: Cart;
  shipping: ShippingQuote;
  tax: number;
  tax_rate: number;
  tax_rule: string | null;
  total: number;
  fingerprint: string;
}

export interface CustomerOrderItem {
  id: string;
  vendor_id: string;
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  status: string;
}

export interface CustomerVendorOrder {
  id: string;
  vendor_id: string;
  vendor_order_number: string;
  status: string;
  subtotal: number;
  commission: number;
  vendor_amount: number;
}

export interface CustomerShipment {
  id: string;
  awb: string;
  status: string;
  current_location: string;
  eta: string | null;
}

export interface CustomerOrder {
  id: string;
  order_number: string;
  status: string;
  payment_method: string;
  payment_status: string;
  subtotal: number;
  discount: number;
  shipping_charge: number;
  tax: number;
  total: number;
  coupon_code: string | null;
  pricing_snapshot: Record<string, unknown>;
  created_at: string;
  items: CustomerOrderItem[];
  vendor_orders: CustomerVendorOrder[];
  shipments: CustomerShipment[];
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface OrderNote {
  id: string;
  note_type: string;
  note: string;
  created_at: string;
}

export interface OrderInvoice {
  invoice_number: string;
  order: CustomerOrder;
  billing_currency: string;
  issued_at: string;
}

export interface TrackingEvent {
  status: string;
  location: string;
  remarks: string;
  timestamp: string;
}

export interface TrackingShipment {
  shipment_id: string;
  awb: string;
  status: string;
  current_location: string;
  events: TrackingEvent[];
}

export interface OrderTracking {
  order_number: string;
  shipments: TrackingShipment[];
}

export interface ReturnRequestSummary {
  id?: string;
  order_id?: string;
  order_item_id?: string | null;
  reason?: string;
  details?: string;
  refund_method?: string;
  status: string;
  requested_at?: string;
  resolved_at?: string | null;
}

export interface StaticPage {
  id: string;
  slug: string;
  title: string;
  summary: string;
  body_markdown: string;
  seo_title: string;
  seo_description: string;
  published_at: string | null;
}
