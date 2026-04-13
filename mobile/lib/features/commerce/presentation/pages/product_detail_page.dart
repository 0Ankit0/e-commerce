import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../data/models/commerce_models.dart';
import '../providers/commerce_provider.dart';

String _currency(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

class ProductDetailPage extends ConsumerStatefulWidget {
  final String productId;

  const ProductDetailPage({super.key, required this.productId});

  @override
  ConsumerState<ProductDetailPage> createState() => _ProductDetailPageState();
}

class _ProductDetailPageState extends ConsumerState<ProductDetailPage> {
  String? _selectedVariantId;
  int _quantity = 1;
  bool _submitting = false;
  bool _wishlistSubmitting = false;

  Future<void> _addToCart(CatalogProduct product) async {
    final variant = product.variants.firstWhere(
      (item) => item.id == _selectedVariantId,
      orElse: () => product.defaultVariant ?? product.variants.first,
    );
    setState(() => _submitting = true);
    try {
      await ref
          .read(commerceRepositoryProvider)
          .addToCart(variantId: variant.id, quantity: _quantity);
      ref.invalidate(cartProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Added to cart'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ErrorHandler.handle(e).message),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _toggleWishlist({
    required CatalogProduct product,
    required bool isWishlisted,
  }) async {
    setState(() => _wishlistSubmitting = true);
    try {
      final repository = ref.read(commerceRepositoryProvider);
      if (isWishlisted) {
        await repository.removeFromWishlist(product.id);
      } else {
        await repository.addToWishlist(product.id);
      }
      ref.invalidate(wishlistProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isWishlisted ? 'Removed from wishlist' : 'Added to wishlist',
            ),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ErrorHandler.handle(e).message),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _wishlistSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final productAsync = ref.watch(productDetailProvider(widget.productId));
    final cartAsync = ref.watch(cartProvider);
    final wishlistProductIds = ref.watch(wishlistProductIdsProvider);
    final cartCount = cartAsync.valueOrNull?.totalQuantity ?? 0;
    final product = productAsync.valueOrNull;
    final isWishlisted =
        product != null && wishlistProductIds.contains(product.id);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Product'),
        actions: [
          IconButton(
            onPressed: product == null || _wishlistSubmitting
                ? null
                : () => _toggleWishlist(
                      product: product,
                      isWishlisted: isWishlisted,
                    ),
            tooltip: isWishlisted ? 'Remove from wishlist' : 'Add to wishlist',
            icon: _wishlistSubmitting
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(
                    isWishlisted ? Icons.favorite : Icons.favorite_border,
                    color: isWishlisted ? Colors.red : null,
                  ),
          ),
          IconButton(
            onPressed: () => context.push(AppConstants.cartRoute),
            icon: Badge(
              isLabelVisible: cartCount > 0,
              label: Text(cartCount > 99 ? '99+' : '$cartCount'),
              child: const Icon(Icons.shopping_bag_outlined),
            ),
          ),
        ],
      ),
      body: productAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(ErrorHandler.handle(err).message),
          ),
        ),
        data: (product) {
          if (product.variants.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'This product is not purchasable yet because no active variants are available.',
                ),
              ),
            );
          }
          final selectedVariant = product.variants.firstWhere(
            (item) =>
                item.id == (_selectedVariantId ?? product.defaultVariant?.id),
            orElse: () => product.defaultVariant ?? product.variants.first,
          );
          final imageUrl = product.images.isNotEmpty
              ? (product.images.firstWhere(
                  (item) => item.isPrimary,
                  orElse: () => product.images.first,
                )).url
              : '';

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              Container(
                height: 320,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(34),
                  gradient: const LinearGradient(
                    colors: [Color(0xFFF7E5CF), Color(0xFFF0ECE6)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: imageUrl.isNotEmpty
                    ? CachedNetworkImage(imageUrl: imageUrl, fit: BoxFit.cover)
                    : const Center(
                        child: Icon(
                          Icons.shopping_bag_outlined,
                          size: 42,
                          color: AppColors.inkSoft,
                        ),
                      ),
              ),
              const SizedBox(height: 20),
              Text(
                product.categoryName ?? 'Product detail',
                style: const TextStyle(
                  fontSize: 11,
                  letterSpacing: 1.6,
                  fontWeight: FontWeight.w700,
                  color: AppColors.inkSoft,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                product.name,
                style: Theme.of(context).textTheme.displayMedium,
              ),
              const SizedBox(height: 12),
              Text(
                product.description.isNotEmpty
                    ? product.description
                    : product.shortDescription,
                style: const TextStyle(height: 1.5, color: AppColors.inkSoft),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Icon(Icons.star_rounded, color: Colors.amber.shade700),
                  const SizedBox(width: 6),
                  Text(
                    '${product.avgRating.toStringAsFixed(1)} • ${product.reviewCount} reviews',
                  ),
                  const Spacer(),
                  Text(
                    _currency(selectedVariant.sellingPrice),
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: AppColors.primary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Column(
                  children: [
                    DropdownButtonFormField<String>(
                      initialValue: _selectedVariantId ??
                          product.defaultVariant?.id ??
                          product.variants.first.id,
                      decoration: const InputDecoration(labelText: 'Variant'),
                      items: product.variants
                          .map(
                            (variant) => DropdownMenuItem(
                              value: variant.id,
                              child: Text(
                                '${variant.name} • ${_currency(variant.sellingPrice)}',
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: (value) =>
                          setState(() => _selectedVariantId = value),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: Container(
                            decoration: BoxDecoration(
                              color: AppColors.surfaceWarm,
                              borderRadius: BorderRadius.circular(18),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                IconButton(
                                  onPressed: () => setState(
                                    () => _quantity =
                                        _quantity > 1 ? _quantity - 1 : 1,
                                  ),
                                  icon: const Icon(Icons.remove),
                                ),
                                Text(
                                  '$_quantity',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                IconButton(
                                  onPressed: () => setState(
                                    () => _quantity =
                                        _quantity < selectedVariant.availableQty
                                            ? _quantity + 1
                                            : _quantity,
                                  ),
                                  icon: const Icon(Icons.add),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          flex: 2,
                          child: FilledButton(
                            onPressed:
                                _submitting || selectedVariant.availableQty == 0
                                    ? null
                                    : () => _addToCart(product),
                            child: Text(
                              _submitting ? 'Adding...' : 'Add to cart',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: () => context.push(AppConstants.cartRoute),
                      child: const Text('Open cart'),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
