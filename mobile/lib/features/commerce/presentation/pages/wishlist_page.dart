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

String _wishlistMoney(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

String _wishlistStatus(String value) => value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word[0].toUpperCase() + word.substring(1))
    .join(' ');

class WishlistPage extends ConsumerStatefulWidget {
  const WishlistPage({super.key});

  @override
  ConsumerState<WishlistPage> createState() => _WishlistPageState();
}

class _WishlistPageState extends ConsumerState<WishlistPage> {
  String? _pendingProductId;

  Future<void> _refreshWishlist() async {
    final _ = await ref.refresh(wishlistProvider.future);
  }

  Future<void> _removeItem(WishlistItemModel item) async {
    setState(() => _pendingProductId = item.productId);
    try {
      await ref
          .read(commerceRepositoryProvider)
          .removeFromWishlist(item.productId);
      ref.invalidate(wishlistProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${item.name} removed from wishlist'),
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
        setState(() => _pendingProductId = null);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final wishlistAsync = ref.watch(wishlistProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Wishlist')),
      body: wishlistAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(ErrorHandler.handle(err).message),
          ),
        ),
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.favorite_border,
                      size: 52,
                      color: AppColors.inkSoft,
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Save products you want to revisit later.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => context.go(AppConstants.homeRoute),
                      child: const Text('Browse products'),
                    ),
                  ],
                ),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refreshWishlist,
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final item = items[index];
                final isBusy = _pendingProductId == item.productId;

                return ListTile(
                  onTap: () =>
                      context.push(AppConstants.productRoute(item.productId)),
                  tileColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(28),
                  ),
                  contentPadding: const EdgeInsets.all(14),
                  leading: Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      gradient: const LinearGradient(
                        colors: [Color(0xFFF7E5CF), Color(0xFFF0ECE6)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: item.imageUrl.isNotEmpty
                        ? CachedNetworkImage(
                            imageUrl: item.imageUrl,
                            fit: BoxFit.cover,
                          )
                        : const Icon(
                            Icons.shopping_bag_outlined,
                            color: AppColors.inkSoft,
                          ),
                  ),
                  title: Text(
                    item.name,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (item.variantName.isNotEmpty) ...[
                          Text(
                            item.variantName,
                            style: const TextStyle(color: AppColors.inkSoft),
                          ),
                          const SizedBox(height: 4),
                        ],
                        if (item.price != null)
                          Text(
                            _wishlistMoney(item.price!),
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              color: AppColors.primary,
                            ),
                          ),
                        if (item.status.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            _wishlistStatus(item.status),
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.inkSoft,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  trailing: isBusy
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : IconButton(
                          tooltip: 'Remove from wishlist',
                          icon: const Icon(Icons.delete_outline),
                          onPressed: () => _removeItem(item),
                        ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
