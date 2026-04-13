class CatalogCategory {
  final String id;
  final String name;
  final String slug;
  final String description;

  const CatalogCategory({
    required this.id,
    required this.name,
    required this.slug,
    required this.description,
  });

  factory CatalogCategory.fromJson(Map<String, dynamic> json) {
    return CatalogCategory(
      id: json['id'].toString(),
      name: json['name'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      description: json['description'] as String? ?? '',
    );
  }
}

class CatalogVariant {
  final String id;
  final String name;
  final String sku;
  final double mrp;
  final double sellingPrice;
  final int availableQty;
  final bool isDefault;
  final bool isActive;
  final Map<String, dynamic> attributes;

  const CatalogVariant({
    required this.id,
    required this.name,
    required this.sku,
    required this.mrp,
    required this.sellingPrice,
    required this.availableQty,
    required this.isDefault,
    required this.isActive,
    required this.attributes,
  });

  factory CatalogVariant.fromJson(Map<String, dynamic> json) {
    return CatalogVariant(
      id: json['id'].toString(),
      name: json['name'] as String? ?? '',
      sku: json['sku'] as String? ?? '',
      mrp: (json['mrp'] as num?)?.toDouble() ?? 0,
      sellingPrice: (json['selling_price'] as num?)?.toDouble() ?? 0,
      availableQty: json['available_qty'] as int? ?? 0,
      isDefault: json['is_default'] as bool? ?? false,
      isActive: json['is_active'] as bool? ?? true,
      attributes: Map<String, dynamic>.from(
        json['attributes'] as Map? ?? const {},
      ),
    );
  }
}

class CatalogProductImage {
  final String id;
  final String url;
  final String thumbnailUrl;
  final String altText;
  final bool isPrimary;

  const CatalogProductImage({
    required this.id,
    required this.url,
    required this.thumbnailUrl,
    required this.altText,
    required this.isPrimary,
  });

  factory CatalogProductImage.fromJson(Map<String, dynamic> json) {
    return CatalogProductImage(
      id: json['id'].toString(),
      url: json['url'] as String? ?? '',
      thumbnailUrl: json['thumbnail_url'] as String? ?? '',
      altText: json['alt_text'] as String? ?? '',
      isPrimary: json['is_primary'] as bool? ?? false,
    );
  }
}

class CatalogProduct {
  final String id;
  final String name;
  final String slug;
  final String shortDescription;
  final String description;
  final bool inStock;
  final bool isFeatured;
  final double avgRating;
  final int reviewCount;
  final int viewCount;
  final double? minSellingPrice;
  final String? categoryName;
  final String? brandName;
  final String? vendorName;
  final String? vendorKycStatus;
  final List<CatalogProductImage> images;
  final List<CatalogVariant> variants;

  const CatalogProduct({
    required this.id,
    required this.name,
    required this.slug,
    required this.shortDescription,
    required this.description,
    required this.inStock,
    required this.isFeatured,
    required this.avgRating,
    required this.reviewCount,
    required this.viewCount,
    required this.minSellingPrice,
    required this.categoryName,
    required this.brandName,
    required this.vendorName,
    required this.vendorKycStatus,
    required this.images,
    required this.variants,
  });

  factory CatalogProduct.fromJson(Map<String, dynamic> json) {
    final category = json['category'] as Map<String, dynamic>?;
    final brand = json['brand'] as Map<String, dynamic>?;
    final vendor = json['vendor'] as Map<String, dynamic>?;
    return CatalogProduct(
      id: json['id'].toString(),
      name: json['name'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      shortDescription: json['short_description'] as String? ?? '',
      description: json['description'] as String? ?? '',
      inStock: json['in_stock'] as bool? ?? false,
      isFeatured: json['is_featured'] as bool? ?? false,
      avgRating: (json['avg_rating'] as num?)?.toDouble() ?? 0,
      reviewCount: json['review_count'] as int? ?? 0,
      viewCount: json['view_count'] as int? ?? 0,
      minSellingPrice: (json['min_selling_price'] as num?)?.toDouble(),
      categoryName: category?['name'] as String?,
      brandName: brand?['name'] as String?,
      vendorName: vendor?['display_name'] as String? ??
          vendor?['business_name'] as String? ??
          json['vendor_name'] as String?,
      vendorKycStatus: (vendor?['kyc_status'] as String?) ??
          (json['vendor_kyc_status'] as String?),
      images: (json['images'] as List<dynamic>? ?? const [])
          .map(
            (item) =>
                CatalogProductImage.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      variants: (json['variants'] as List<dynamic>? ?? const [])
          .map((item) => CatalogVariant.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  CatalogVariant? get defaultVariant {
    if (variants.isEmpty) {
      return null;
    }
    return variants.firstWhere(
      (variant) => variant.isDefault,
      orElse: () => variants.first,
    );
  }
}

class WishlistItemModel {
  final String id;
  final String productId;
  final String name;
  final String slug;
  final String status;
  final String imageUrl;
  final double? price;
  final String? variantId;
  final String variantName;

  const WishlistItemModel({
    required this.id,
    required this.productId,
    required this.name,
    required this.slug,
    required this.status,
    required this.imageUrl,
    required this.price,
    required this.variantId,
    required this.variantName,
  });

  factory WishlistItemModel.fromJson(Map<String, dynamic> json) {
    return WishlistItemModel(
      id: json['id'].toString(),
      productId: json['product_id']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      status: json['status'] as String? ?? '',
      imageUrl: json['image_url'] as String? ?? '',
      price: (json['price'] as num?)?.toDouble(),
      variantId: json['variant_id']?.toString(),
      variantName: json['variant_name'] as String? ?? '',
    );
  }
}

class CartItem {
  final String id;
  final String variantId;
  final String? productId;
  final String productName;
  final String variantName;
  final String sku;
  final int quantity;
  final double unitPrice;
  final double lineTotal;
  final int availableQty;

  const CartItem({
    required this.id,
    required this.variantId,
    required this.productId,
    required this.productName,
    required this.variantName,
    required this.sku,
    required this.quantity,
    required this.unitPrice,
    required this.lineTotal,
    required this.availableQty,
  });

  factory CartItem.fromJson(Map<String, dynamic> json) {
    return CartItem(
      id: json['id'].toString(),
      variantId: json['variant_id'].toString(),
      productId: json['product_id']?.toString(),
      productName: json['product_name'] as String? ?? '',
      variantName: json['variant_name'] as String? ?? '',
      sku: json['sku'] as String? ?? '',
      quantity: json['quantity'] as int? ?? 0,
      unitPrice: (json['unit_price'] as num?)?.toDouble() ?? 0,
      lineTotal: (json['line_total'] as num?)?.toDouble() ?? 0,
      availableQty: json['available_qty'] as int? ?? 0,
    );
  }
}

class CartModel {
  final String id;
  final String? couponCode;
  final List<CartItem> items;
  final double subtotal;
  final double discount;
  final double total;

  const CartModel({
    required this.id,
    required this.couponCode,
    required this.items,
    required this.subtotal,
    required this.discount,
    required this.total,
  });

  factory CartModel.fromJson(Map<String, dynamic> json) {
    return CartModel(
      id: json['id'].toString(),
      couponCode: json['coupon_code'] as String?,
      items: (json['items'] as List<dynamic>? ?? const [])
          .map((item) => CartItem.fromJson(item as Map<String, dynamic>))
          .toList(),
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0,
      discount: (json['discount'] as num?)?.toDouble() ?? 0,
      total: (json['total'] as num?)?.toDouble() ?? 0,
    );
  }

  int get totalQuantity => items.fold(0, (sum, item) => sum + item.quantity);
}

class AddressModel {
  final String id;
  final String name;
  final String phone;
  final String line1;
  final String line2;
  final String city;
  final String state;
  final String pincode;
  final String country;
  final String landmark;
  final String type;
  final bool isDefault;

  const AddressModel({
    required this.id,
    required this.name,
    required this.phone,
    required this.line1,
    required this.line2,
    required this.city,
    required this.state,
    required this.pincode,
    required this.country,
    required this.landmark,
    required this.type,
    required this.isDefault,
  });

  factory AddressModel.fromJson(Map<String, dynamic> json) {
    return AddressModel(
      id: json['id'].toString(),
      name: json['name'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      line1: json['line1'] as String? ?? '',
      line2: json['line2'] as String? ?? '',
      city: json['city'] as String? ?? '',
      state: json['state'] as String? ?? '',
      pincode: json['pincode'] as String? ?? '',
      country: json['country'] as String? ?? '',
      landmark: json['landmark'] as String? ?? '',
      type: json['type'] as String? ?? 'home',
      isDefault: json['is_default'] as bool? ?? false,
    );
  }

  String get compactLabel => '$line1, $city, $state $pincode';
}

class ShippingQuote {
  final bool serviceable;
  final String? zoneCode;
  final double shippingRate;
  final bool codEnabled;
  final String? shippingOption;

  const ShippingQuote({
    required this.serviceable,
    required this.zoneCode,
    required this.shippingRate,
    required this.codEnabled,
    required this.shippingOption,
  });

  factory ShippingQuote.fromJson(Map<String, dynamic> json) {
    return ShippingQuote(
      serviceable: json['serviceable'] as bool? ?? false,
      zoneCode: json['zone_code'] as String?,
      shippingRate: (json['shipping_rate'] as num?)?.toDouble() ?? 0,
      codEnabled: json['cod_enabled'] as bool? ?? false,
      shippingOption: json['shipping_option'] as String?,
    );
  }
}

class CheckoutQuote {
  final CartModel cart;
  final ShippingQuote shipping;
  final double tax;
  final double taxRate;
  final String? taxRule;
  final double total;
  final String fingerprint;

  const CheckoutQuote({
    required this.cart,
    required this.shipping,
    required this.tax,
    required this.taxRate,
    required this.taxRule,
    required this.total,
    required this.fingerprint,
  });

  factory CheckoutQuote.fromJson(Map<String, dynamic> json) {
    return CheckoutQuote(
      cart: CartModel.fromJson(json['cart'] as Map<String, dynamic>),
      shipping: ShippingQuote.fromJson(
        json['shipping'] as Map<String, dynamic>,
      ),
      tax: (json['tax'] as num?)?.toDouble() ?? 0,
      taxRate: (json['tax_rate'] as num?)?.toDouble() ?? 0,
      taxRule: json['tax_rule'] as String?,
      total: (json['total'] as num?)?.toDouble() ?? 0,
      fingerprint: json['fingerprint'] as String? ?? '',
    );
  }
}

class CustomerOrderItem {
  final String id;
  final String productId;
  final String productName;
  final String variantName;
  final int quantity;
  final double totalPrice;
  final String status;

  const CustomerOrderItem({
    required this.id,
    required this.productId,
    required this.productName,
    required this.variantName,
    required this.quantity,
    required this.totalPrice,
    required this.status,
  });

  factory CustomerOrderItem.fromJson(Map<String, dynamic> json) {
    return CustomerOrderItem(
      id: json['id'].toString(),
      productId: json['product_id'].toString(),
      productName: json['product_name'] as String? ?? '',
      variantName: json['variant_name'] as String? ?? '',
      quantity: json['quantity'] as int? ?? 0,
      totalPrice: (json['total_price'] as num?)?.toDouble() ?? 0,
      status: json['status'] as String? ?? '',
    );
  }
}

class CustomerShipment {
  final String id;
  final String awb;
  final String status;
  final String currentLocation;
  final String? eta;

  const CustomerShipment({
    required this.id,
    required this.awb,
    required this.status,
    required this.currentLocation,
    required this.eta,
  });

  factory CustomerShipment.fromJson(Map<String, dynamic> json) {
    return CustomerShipment(
      id: json['id'].toString(),
      awb: json['awb'] as String? ?? '',
      status: json['status'] as String? ?? '',
      currentLocation: json['current_location'] as String? ?? '',
      eta: json['eta'] as String?,
    );
  }
}

class CustomerOrder {
  final String id;
  final String orderNumber;
  final String status;
  final String paymentMethod;
  final String paymentStatus;
  final double subtotal;
  final double discount;
  final double shippingCharge;
  final double tax;
  final double total;
  final String? couponCode;
  final String createdAt;
  final List<CustomerOrderItem> items;
  final List<CustomerShipment> shipments;

  const CustomerOrder({
    required this.id,
    required this.orderNumber,
    required this.status,
    required this.paymentMethod,
    required this.paymentStatus,
    required this.subtotal,
    required this.discount,
    required this.shippingCharge,
    required this.tax,
    required this.total,
    required this.couponCode,
    required this.createdAt,
    required this.items,
    required this.shipments,
  });

  factory CustomerOrder.fromJson(Map<String, dynamic> json) {
    return CustomerOrder(
      id: json['id'].toString(),
      orderNumber: json['order_number'] as String? ?? '',
      status: json['status'] as String? ?? '',
      paymentMethod: json['payment_method'] as String? ?? '',
      paymentStatus: json['payment_status'] as String? ?? '',
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0,
      discount: (json['discount'] as num?)?.toDouble() ?? 0,
      shippingCharge: (json['shipping_charge'] as num?)?.toDouble() ?? 0,
      tax: (json['tax'] as num?)?.toDouble() ?? 0,
      total: (json['total'] as num?)?.toDouble() ?? 0,
      couponCode: json['coupon_code'] as String?,
      createdAt: json['created_at'] as String? ?? '',
      items: (json['items'] as List<dynamic>? ?? const [])
          .map(
            (item) => CustomerOrderItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      shipments: (json['shipments'] as List<dynamic>? ?? const [])
          .map(
            (item) => CustomerShipment.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }
}

class TrackingEvent {
  final String status;
  final String location;
  final String remarks;
  final String timestamp;

  const TrackingEvent({
    required this.status,
    required this.location,
    required this.remarks,
    required this.timestamp,
  });

  factory TrackingEvent.fromJson(Map<String, dynamic> json) {
    return TrackingEvent(
      status: json['status'] as String? ?? '',
      location: json['location'] as String? ?? '',
      remarks: json['remarks'] as String? ?? '',
      timestamp: json['timestamp'] as String? ?? '',
    );
  }
}

class TrackingShipment {
  final String shipmentId;
  final String awb;
  final String status;
  final String currentLocation;
  final List<TrackingEvent> events;

  const TrackingShipment({
    required this.shipmentId,
    required this.awb,
    required this.status,
    required this.currentLocation,
    required this.events,
  });

  factory TrackingShipment.fromJson(Map<String, dynamic> json) {
    return TrackingShipment(
      shipmentId: json['shipment_id'].toString(),
      awb: json['awb'] as String? ?? '',
      status: json['status'] as String? ?? '',
      currentLocation: json['current_location'] as String? ?? '',
      events: (json['events'] as List<dynamic>? ?? const [])
          .map((item) => TrackingEvent.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class OrderTracking {
  final String orderNumber;
  final List<TrackingShipment> shipments;

  const OrderTracking({required this.orderNumber, required this.shipments});

  factory OrderTracking.fromJson(Map<String, dynamic> json) {
    return OrderTracking(
      orderNumber: json['order_number'] as String? ?? '',
      shipments: (json['shipments'] as List<dynamic>? ?? const [])
          .map(
            (item) => TrackingShipment.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }
}

class ReturnRequestCreatePayload {
  final String orderId;
  final String? orderItemId;
  final int quantity;
  final String reason;
  final String details;
  final String refundMethod;

  const ReturnRequestCreatePayload({
    required this.orderId,
    this.orderItemId,
    required this.quantity,
    required this.reason,
    this.details = '',
    this.refundMethod = 'original',
  });

  Map<String, dynamic> toJson() {
    return {
      'order_id': orderId,
      if (orderItemId != null && orderItemId!.isNotEmpty)
        'order_item_id': orderItemId,
      'quantity': quantity,
      'reason': reason,
      'details': details,
      'refund_method': refundMethod,
    };
  }
}

class ReturnRequestSubmission {
  final String returnRequestId;
  final String status;

  const ReturnRequestSubmission({
    required this.returnRequestId,
    required this.status,
  });

  factory ReturnRequestSubmission.fromJson(Map<String, dynamic> json) {
    return ReturnRequestSubmission(
      returnRequestId: json['return_request_id']?.toString() ?? '',
      status: json['status'] as String? ?? '',
    );
  }
}

class ReturnRequestModel {
  final String id;
  final String orderId;
  final String? orderItemId;
  final String userId;
  final String reason;
  final String details;
  final int quantity;
  final String refundMethod;
  final String status;
  final int returnWindowDays;
  final String? eligibleUntil;
  final String createdAt;
  final String? resolvedAt;

  const ReturnRequestModel({
    required this.id,
    required this.orderId,
    required this.orderItemId,
    required this.userId,
    required this.reason,
    required this.details,
    required this.quantity,
    required this.refundMethod,
    required this.status,
    required this.returnWindowDays,
    required this.eligibleUntil,
    required this.createdAt,
    required this.resolvedAt,
  });

  factory ReturnRequestModel.fromJson(Map<String, dynamic> json) {
    return ReturnRequestModel(
      id: json['id']?.toString() ?? '',
      orderId: json['order_id']?.toString() ?? '',
      orderItemId: json['order_item_id']?.toString(),
      userId: json['user_id']?.toString() ?? '',
      reason: json['reason'] as String? ?? '',
      details: json['details'] as String? ?? '',
      quantity: json['quantity'] as int? ?? 0,
      refundMethod: json['refund_method'] as String? ?? 'original',
      status: json['status'] as String? ?? '',
      returnWindowDays: json['return_window_days'] as int? ?? 0,
      eligibleUntil: json['eligible_until'] as String?,
      createdAt: json['created_at'] as String? ?? '',
      resolvedAt: json['resolved_at'] as String?,
    );
  }
}

class ReturnTimelineEvent {
  final String id;
  final String eventType;
  final String message;
  final Map<String, dynamic> payload;
  final String createdAt;

  const ReturnTimelineEvent({
    required this.id,
    required this.eventType,
    required this.message,
    required this.payload,
    required this.createdAt,
  });

  factory ReturnTimelineEvent.fromJson(Map<String, dynamic> json) {
    return ReturnTimelineEvent(
      id: json['id']?.toString() ?? '',
      eventType: json['event_type'] as String? ?? '',
      message: json['message'] as String? ?? '',
      payload: Map<String, dynamic>.from(json['payload'] as Map? ?? const {}),
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}
