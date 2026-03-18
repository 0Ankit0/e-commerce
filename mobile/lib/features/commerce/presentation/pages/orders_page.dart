import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../providers/commerce_provider.dart';

String _orderMoney(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

String _dateLabel(String value) {
  try {
    return DateFormat('MMM d, y').format(DateTime.parse(value).toLocal());
  } catch (_) {
    return value;
  }
}

String _statusLabel(String value) => value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word[0].toUpperCase() + word.substring(1))
    .join(' ');

class OrdersPage extends ConsumerWidget {
  const OrdersPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(ordersProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My Orders')),
      body: ordersAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) =>
            Center(child: Text(ErrorHandler.handle(err).message)),
        data: (orders) {
          if (orders.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.receipt_long_outlined,
                      size: 48,
                      color: AppColors.inkSoft,
                    ),
                    const SizedBox(height: 12),
                    const Text('You have not placed any orders yet.'),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => context.go(AppConstants.homeRoute),
                      child: const Text('Start shopping'),
                    ),
                  ],
                ),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(ordersProvider);
            },
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              itemCount: orders.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final order = orders[index];
                return ListTile(
                  tileColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(26),
                  ),
                  contentPadding: const EdgeInsets.all(18),
                  title: Text(
                    order.orderNumber,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${order.items.length} items • ${_dateLabel(order.createdAt)}',
                          style: const TextStyle(color: AppColors.inkSoft),
                        ),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          children: [
                            Chip(label: Text(_statusLabel(order.status))),
                            Chip(
                              label: Text(_statusLabel(order.paymentStatus)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        _orderMoney(order.total),
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 4),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                  onTap: () =>
                      context.push(AppConstants.orderDetailRoute(order.id)),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
