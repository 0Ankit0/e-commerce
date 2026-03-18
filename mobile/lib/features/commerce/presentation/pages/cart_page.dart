import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../data/models/commerce_models.dart';
import '../providers/commerce_provider.dart';

String _money(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

class CartPage extends ConsumerWidget {
  const CartPage({super.key});

  Future<void> _updateQuantity(
    WidgetRef ref, {
    required BuildContext context,
    required CartItem item,
    required int quantity,
  }) async {
    try {
      await ref
          .read(commerceRepositoryProvider)
          .updateCartItem(itemId: item.id, quantity: quantity);
      ref.invalidate(cartProvider);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ErrorHandler.handle(e).message),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _removeItem(
    WidgetRef ref, {
    required BuildContext context,
    required String itemId,
  }) async {
    try {
      await ref.read(commerceRepositoryProvider).removeCartItem(itemId);
      ref.invalidate(cartProvider);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ErrorHandler.handle(e).message),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cartAsync = ref.watch(cartProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Cart')),
      body: cartAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) =>
            Center(child: Text(ErrorHandler.handle(err).message)),
        data: (cart) {
          if (cart.items.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.shopping_bag_outlined,
                      size: 48,
                      color: AppColors.inkSoft,
                    ),
                    const SizedBox(height: 12),
                    const Text('Your cart is empty right now.'),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => context.go(AppConstants.homeRoute),
                      child: const Text('Keep shopping'),
                    ),
                  ],
                ),
              ),
            );
          }

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              ...cart.items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(26),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.productName,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          item.variantName,
                          style: const TextStyle(color: AppColors.inkSoft),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                decoration: BoxDecoration(
                                  color: AppColors.surfaceWarm,
                                  borderRadius: BorderRadius.circular(18),
                                ),
                                child: Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
                                  children: [
                                    IconButton(
                                      onPressed: item.quantity > 1
                                          ? () => _updateQuantity(
                                                ref,
                                                context: context,
                                                item: item,
                                                quantity: item.quantity - 1,
                                              )
                                          : null,
                                      icon: const Icon(Icons.remove),
                                    ),
                                    Text(
                                      '${item.quantity}',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    IconButton(
                                      onPressed:
                                          item.quantity < item.availableQty
                                              ? () => _updateQuantity(
                                                    ref,
                                                    context: context,
                                                    item: item,
                                                    quantity: item.quantity + 1,
                                                  )
                                              : null,
                                      icon: const Icon(Icons.add),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text(
                              _money(item.lineTotal),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            IconButton(
                              onPressed: () => _removeItem(
                                ref,
                                context: context,
                                itemId: item.id,
                              ),
                              icon: const Icon(Icons.delete_outline),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Summary',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 14),
                    _SummaryRow(
                      label: 'Subtotal',
                      value: _money(cart.subtotal),
                    ),
                    _SummaryRow(
                      label: 'Discount',
                      value: '- ${_money(cart.discount)}',
                    ),
                    const Divider(height: 26),
                    _SummaryRow(
                      label: 'Cart total',
                      value: _money(cart.total),
                      emphasize: true,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => context.push(AppConstants.checkoutRoute),
                      child: const Text('Continue to checkout'),
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

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final bool emphasize;

  const _SummaryRow({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      fontSize: emphasize ? 16 : 14,
      fontWeight: emphasize ? FontWeight.w700 : FontWeight.w500,
      color: AppColors.primary,
    );
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: style),
        Text(value, style: style),
      ],
    );
  }
}
