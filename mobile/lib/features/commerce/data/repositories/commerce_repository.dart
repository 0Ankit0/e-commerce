import 'package:dio/dio.dart';
import '../../../../core/error/error_handler.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../models/commerce_models.dart';

class CommerceRepository {
  final DioClient _dioClient;

  CommerceRepository(this._dioClient);

  Future<List<CatalogProduct>> getProducts({
    String? query,
    String? categoryId,
    bool? featuredOnly,
    int limit = 20,
  }) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.products,
        queryParameters: {
          if (query != null && query.isNotEmpty) 'q': query,
          if (categoryId != null && categoryId.isNotEmpty)
            'category': categoryId,
          if (featuredOnly != null) 'is_featured': featuredOnly,
          'limit': limit,
        },
      );
      final payload = response.data as Map<String, dynamic>;
      final items = payload['items'] as List<dynamic>? ?? const [];
      return items
          .map((item) => CatalogProduct.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<CatalogCategory>> getCategories() async {
    try {
      final response = await _dioClient.dio.get(ApiEndpoints.categories);
      final payload = response.data as Map<String, dynamic>;
      final items = payload['items'] as List<dynamic>? ?? const [];
      return items
          .map((item) => CatalogCategory.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CatalogProduct> getProduct(String productId) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.productById(productId),
      );
      final payload = response.data as Map<String, dynamic>;
      return CatalogProduct.fromJson(
        payload['product'] as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<WishlistItemModel>> getWishlist() async {
    try {
      final response = await _dioClient.dio.get(ApiEndpoints.wishlist);
      final payload = response.data as Map<String, dynamic>;
      final items = payload['items'] as List<dynamic>? ?? const [];
      return items
          .map(
            (item) => WishlistItemModel.fromJson(item as Map<String, dynamic>),
          )
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> addToWishlist(String productId) async {
    try {
      await _dioClient.dio.post(ApiEndpoints.wishlistByProduct(productId));
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> removeFromWishlist(String productId) async {
    try {
      await _dioClient.dio.delete(ApiEndpoints.wishlistByProduct(productId));
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CartModel> getCart() async {
    try {
      final response = await _dioClient.dio.get(ApiEndpoints.cart);
      return CartModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CartModel> addToCart({
    required String variantId,
    required int quantity,
  }) async {
    try {
      final response = await _dioClient.dio.post(
        ApiEndpoints.cartItems,
        data: {'variant_id': variantId, 'quantity': quantity},
      );
      return CartModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CartModel> updateCartItem({
    required String itemId,
    required int quantity,
  }) async {
    try {
      final response = await _dioClient.dio.patch(
        ApiEndpoints.cartItemById(itemId),
        data: {'quantity': quantity},
      );
      return CartModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CartModel> removeCartItem(String itemId) async {
    try {
      final response = await _dioClient.dio.delete(
        ApiEndpoints.cartItemById(itemId),
      );
      return CartModel.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<AddressModel>> getAddresses() async {
    try {
      final response = await _dioClient.dio.get(ApiEndpoints.addresses);
      final payload = response.data as Map<String, dynamic>;
      final items = payload['items'] as List<dynamic>? ?? const [];
      return items
          .map((item) => AddressModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<AddressModel> createAddress(Map<String, dynamic> payload) async {
    try {
      final response = await _dioClient.dio.post(
        ApiEndpoints.addresses,
        data: payload,
      );
      return AddressModel.fromJson(
        (response.data as Map<String, dynamic>)['address']
            as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<AddressModel> setDefaultAddress(String addressId) async {
    try {
      final response = await _dioClient.dio.post(
        ApiEndpoints.addressDefault(addressId),
      );
      return AddressModel.fromJson(
        (response.data as Map<String, dynamic>)['address']
            as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CheckoutQuote> getCheckoutQuote({
    required String addressId,
    required String paymentMethod,
  }) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.checkoutQuote,
        queryParameters: {
          'address_id': addressId,
          'payment_method': paymentMethod,
        },
      );
      return CheckoutQuote.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CustomerOrder> checkout({
    required String addressId,
    required String paymentMethod,
    required String quoteFingerprint,
    String? paymentTransactionId,
    String notes = '',
  }) async {
    try {
      final response = await _dioClient.dio.post(
        ApiEndpoints.checkout,
        data: {
          'address_id': addressId,
          'payment_method': paymentMethod,
          if (paymentTransactionId != null && paymentTransactionId.isNotEmpty)
            'payment_transaction_id': paymentTransactionId,
          'quote_fingerprint': quoteFingerprint,
          'notes': notes,
        },
        options: Options(
          headers: {
            'Idempotency-Key':
                '$addressId:$paymentMethod:$quoteFingerprint:${paymentTransactionId ?? 'direct'}',
          },
        ),
      );
      return CustomerOrder.fromJson(
        (response.data as Map<String, dynamic>)['order']
            as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<CustomerOrder>> getOrders() async {
    try {
      final response = await _dioClient.dio.get(ApiEndpoints.orders);
      final payload = response.data as Map<String, dynamic>;
      final items = payload['items'] as List<dynamic>? ?? const [];
      return items
          .map((item) => CustomerOrder.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CustomerOrder> getOrder(String orderId) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.orderById(orderId),
      );
      return CustomerOrder.fromJson(
        (response.data as Map<String, dynamic>)['order']
            as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<CustomerOrder> cancelOrder(String orderId) async {
    try {
      final response = await _dioClient.dio.post(
        ApiEndpoints.cancelOrder(orderId),
      );
      return CustomerOrder.fromJson(
        (response.data as Map<String, dynamic>)['order']
            as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<ReturnRequestSubmission> createReturnRequest(
    ReturnRequestCreatePayload payload,
  ) async {
    try {
      final response = await _dioClient.dio.post(
        ApiEndpoints.returns,
        data: payload.toJson(),
      );
      return ReturnRequestSubmission.fromJson(
        response.data as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<ReturnRequestModel> getReturnRequest(String returnRequestId) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.returnById(returnRequestId),
      );
      return ReturnRequestModel.fromJson(
        (response.data as Map<String, dynamic>)['return_request']
            as Map<String, dynamic>,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<ReturnTimelineEvent>> getReturnTimeline(
    String returnRequestId,
  ) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.returnTimeline(returnRequestId),
      );
      final payload = response.data as Map<String, dynamic>;
      final items = payload['items'] as List<dynamic>? ?? const [];
      return items
          .map(
            (item) => ReturnTimelineEvent.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<OrderTracking> getOrderTracking(String orderId) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.orderTracking(orderId),
      );
      return OrderTracking.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }
}
