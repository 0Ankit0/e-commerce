import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../commerce/data/models/commerce_models.dart';
import '../../../commerce/presentation/providers/commerce_provider.dart';
import '../../../notifications/presentation/providers/notification_provider.dart';

String _currency(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

String _kycLabel(String? status) {
  switch (status) {
    case 'approved':
      return 'KYC verified vendor';
    case 'under_review':
      return 'KYC under review';
    case 'resubmission_required':
      return 'KYC resubmission requested';
    case 'rejected':
      return 'KYC rejected';
    case 'submitted':
      return 'KYC submitted';
    default:
      return 'Vendor verification pending';
  }
}

Color _kycColor(String? status) {
  switch (status) {
    case 'approved':
      return Colors.green.shade700;
    case 'rejected':
      return Colors.red.shade700;
    case 'resubmission_required':
      return Colors.orange.shade700;
    default:
      return AppColors.inkSoft;
  }
}

class HomeTab extends ConsumerStatefulWidget {
  const HomeTab({super.key});

  @override
  ConsumerState<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends ConsumerState<HomeTab> {
  String _query = '';
  String _categoryId = '';

  @override
  Widget build(BuildContext context) {
    final productsAsync = ref.watch(
      catalogProductsProvider((query: _query, categoryId: _categoryId)),
    );
    final featuredAsync = ref.watch(featuredProductsProvider);
    final categoriesAsync = ref.watch(categoriesProvider);
    final cartAsync = ref.watch(cartProvider);
    final wishlistCount = ref.watch(wishlistCountProvider);

    final theme = Theme.of(context);
    final cartCount = cartAsync.valueOrNull?.totalQuantity ?? 0;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Northstar Market',
              style: theme.textTheme.headlineMedium?.copyWith(fontSize: 28),
            ),
            const Text(
              'User app for ordering and delivery tracking',
              style: TextStyle(fontSize: 12, color: AppColors.inkSoft),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: () => context.push(AppConstants.wishlistRoute),
            icon: Badge(
              isLabelVisible: wishlistCount > 0,
              label: Text(wishlistCount > 99 ? '99+' : '$wishlistCount'),
              child: const Icon(Icons.favorite_border),
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
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(featuredProductsProvider);
          ref.invalidate(categoriesProvider);
          ref.invalidate(
            catalogProductsProvider((query: _query, categoryId: _categoryId)),
          );
          ref.invalidate(cartProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(32),
                gradient: const LinearGradient(
                  colors: [
                    Color(0xFFFFF7EC),
                    Color(0xFFF2E4CE),
                    Color(0xFFE2F0EB),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'From browse to doorstep, inside one app.',
                    style: theme.textTheme.displayMedium?.copyWith(
                      fontSize: 38,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Discover products, manage your cart, place an order, and follow delivery milestones from shipment pickup to arrival.',
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.5,
                      color: AppColors.inkSoft,
                    ),
                  ),
                  const SizedBox(height: 18),
                  TextField(
                    onChanged: (value) => setState(() => _query = value),
                    decoration: InputDecoration(
                      hintText: 'Search products, makers, materials...',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _query.isNotEmpty
                          ? IconButton(
                              onPressed: () => setState(() => _query = ''),
                              icon: const Icon(Icons.close),
                            )
                          : null,
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 500.ms).slideY(begin: 0.06),
            const SizedBox(height: 20),
            Text(
              'Collections',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            categoriesAsync.when(
              loading: () => const SizedBox(
                height: 44,
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (_, __) =>
                  const Text('Unable to load collections right now.'),
              data: (categories) => SizedBox(
                height: 44,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: categories.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(width: 10),
                  itemBuilder: (context, index) {
                    if (index == 0) {
                      return ChoiceChip(
                        label: const Text('All'),
                        selected: _categoryId.isEmpty,
                        onSelected: (_) => setState(() => _categoryId = ''),
                      );
                    }
                    final category = categories[index - 1];
                    return ChoiceChip(
                      label: Text(category.name),
                      selected: _categoryId == category.id,
                      onSelected: (_) =>
                          setState(() => _categoryId = category.id),
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Featured now',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                TextButton(
                  onPressed: () => context.go(AppConstants.ordersRoute),
                  child: const Text('My orders'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            featuredAsync.when(
              loading: () => const SizedBox(
                height: 220,
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (_, __) => const Text('Unable to load featured products.'),
              data: (products) => SizedBox(
                height: 230,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: products.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 14),
                  itemBuilder: (context, index) {
                    final product = products[index];
                    return _FeaturedProductCard(product: product);
                  },
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              _query.isEmpty && _categoryId.isEmpty
                  ? 'Shop all'
                  : 'Filtered results',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            productsAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.only(top: 32),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (_, __) => const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text('We could not load the catalog right now.'),
              ),
              data: (products) {
                if (products.isEmpty) {
                  return Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: const Text(
                      'No products match your current search yet. Try a broader phrase or another collection.',
                      style: TextStyle(color: AppColors.inkSoft),
                    ),
                  );
                }
                return Column(
                  children: products
                      .map(
                        (product) => Padding(
                          padding: const EdgeInsets.only(bottom: 14),
                          child: _CatalogProductCard(product: product),
                        ),
                      )
                      .toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _FeaturedProductCard extends StatelessWidget {
  final CatalogProduct product;

  const _FeaturedProductCard({required this.product});

  @override
  Widget build(BuildContext context) {
    final imageUrl = product.images.isNotEmpty
        ? (product.images.firstWhere(
            (item) => item.isPrimary,
            orElse: () => product.images.first,
          )).url
        : '';

    return GestureDetector(
      onTap: () => context.push(AppConstants.productRoute(product.id)),
      child: Container(
        width: 230,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(30),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(22),
                  gradient: const LinearGradient(
                    colors: [Color(0xFFF7E7D4), Color(0xFFF1EEE8)],
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
                          color: AppColors.inkSoft,
                          size: 34,
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 14),
            Text(
              product.categoryName ?? 'Curated pick',
              style: const TextStyle(
                fontSize: 11,
                letterSpacing: 1.4,
                fontWeight: FontWeight.w700,
                color: AppColors.inkSoft,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              product.name,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              _currency(product.minSellingPrice ?? 0),
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              _kycLabel(product.vendorKycStatus),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11,
                color: _kycColor(product.vendorKycStatus),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogProductCard extends StatelessWidget {
  final CatalogProduct product;

  const _CatalogProductCard({required this.product});

  @override
  Widget build(BuildContext context) {
    final imageUrl = product.images.isNotEmpty
        ? (product.images.firstWhere(
            (item) => item.isPrimary,
            orElse: () => product.images.first,
          )).url
        : '';

    return GestureDetector(
      onTap: () => context.push(AppConstants.productRoute(product.id)),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(28),
        ),
        child: Row(
          children: [
            Container(
              width: 112,
              height: 112,
              margin: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                gradient: const LinearGradient(
                  colors: [Color(0xFFF6E2CA), Color(0xFFF1ECE4)],
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
                        color: AppColors.inkSoft,
                      ),
                    ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(4, 18, 18, 18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      product.categoryName ?? 'Product',
                      style: const TextStyle(
                        fontSize: 11,
                        letterSpacing: 1.4,
                        fontWeight: FontWeight.w700,
                        color: AppColors.inkSoft,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      product.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      product.shortDescription.isNotEmpty
                          ? product.shortDescription
                          : product.description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.inkSoft,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 10),
                    if ((product.vendorName ?? '').isNotEmpty) ...[
                      Text(
                        product.vendorName!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.inkSoft,
                        ),
                      ),
                      const SizedBox(height: 6),
                    ],
                    Text(
                      _kycLabel(product.vendorKycStatus),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: _kycColor(product.vendorKycStatus),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(
                          Icons.star_rounded,
                          color: Colors.amber.shade700,
                          size: 18,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${product.avgRating.toStringAsFixed(1)} • ${product.reviewCount} reviews',
                        ),
                        const Spacer(),
                        Text(
                          _currency(product.minSellingPrice ?? 0),
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class HomePage extends ConsumerWidget {
  final StatefulNavigationShell navigationShell;

  const HomePage({super.key, required this.navigationShell});

  static const _destinations = [
    NavigationDestination(
      icon: Icon(Icons.storefront_outlined),
      selectedIcon: Icon(Icons.storefront),
      label: 'Shop',
    ),
    NavigationDestination(
      icon: Icon(Icons.receipt_long_outlined),
      selectedIcon: Icon(Icons.receipt_long),
      label: 'Orders',
    ),
    NavigationDestination(
      icon: Icon(Icons.notifications_outlined),
      selectedIcon: Icon(Icons.notifications),
      label: 'Notifications',
    ),
    NavigationDestination(
      icon: Icon(Icons.person_outline),
      selectedIcon: Icon(Icons.person),
      label: 'Profile',
    ),
  ];

  void _onDestinationSelected(int index) {
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unreadAsync = ref.watch(unreadCountProvider);
    final unreadCount = unreadAsync.valueOrNull ?? 0;

    final destinations = [
      _destinations[0],
      _destinations[1],
      NavigationDestination(
        icon: Badge(
          isLabelVisible: unreadCount > 0,
          label: Text(unreadCount > 99 ? '99+' : '$unreadCount'),
          child: const Icon(Icons.notifications_outlined),
        ),
        selectedIcon: Badge(
          isLabelVisible: unreadCount > 0,
          label: Text(unreadCount > 99 ? '99+' : '$unreadCount'),
          child: const Icon(Icons.notifications),
        ),
        label: 'Notifications',
      ),
      _destinations[3],
    ];

    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: _onDestinationSelected,
        destinations: destinations,
      ),
    );
  }
}
