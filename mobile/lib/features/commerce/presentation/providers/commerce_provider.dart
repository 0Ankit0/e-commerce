import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/providers/dio_provider.dart';
import '../../data/models/commerce_models.dart';
import '../../data/repositories/commerce_repository.dart';

final commerceRepositoryProvider = Provider<CommerceRepository>((ref) {
  return CommerceRepository(ref.watch(dioClientProvider));
});

final catalogProductsProvider = FutureProvider.family<List<CatalogProduct>,
    ({String query, String categoryId})>((ref, params) async {
  return ref.watch(commerceRepositoryProvider).getProducts(
        query: params.query.isEmpty ? null : params.query,
        categoryId: params.categoryId.isEmpty ? null : params.categoryId,
        limit: 24,
      );
});

final featuredProductsProvider = FutureProvider<List<CatalogProduct>>((
  ref,
) async {
  return ref
      .watch(commerceRepositoryProvider)
      .getProducts(featuredOnly: true, limit: 8);
});

final categoriesProvider = FutureProvider<List<CatalogCategory>>((ref) async {
  return ref.watch(commerceRepositoryProvider).getCategories();
});

final productDetailProvider = FutureProvider.family<CatalogProduct, String>((
  ref,
  productId,
) async {
  return ref.watch(commerceRepositoryProvider).getProduct(productId);
});

final cartProvider = FutureProvider<CartModel>((ref) async {
  return ref.watch(commerceRepositoryProvider).getCart();
});

final addressesProvider = FutureProvider<List<AddressModel>>((ref) async {
  return ref.watch(commerceRepositoryProvider).getAddresses();
});

final checkoutQuoteProvider = FutureProvider.family<CheckoutQuote,
    ({String addressId, String paymentMethod})>((ref, params) async {
  return ref.watch(commerceRepositoryProvider).getCheckoutQuote(
        addressId: params.addressId,
        paymentMethod: params.paymentMethod,
      );
});

final ordersProvider = FutureProvider<List<CustomerOrder>>((ref) async {
  return ref.watch(commerceRepositoryProvider).getOrders();
});

final orderDetailProvider = FutureProvider.family<CustomerOrder, String>((
  ref,
  orderId,
) async {
  return ref.watch(commerceRepositoryProvider).getOrder(orderId);
});

final orderTrackingProvider = FutureProvider.family<OrderTracking, String>((
  ref,
  orderId,
) async {
  return ref.watch(commerceRepositoryProvider).getOrderTracking(orderId);
});
