import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../data/models/commerce_models.dart';
import '../providers/commerce_provider.dart';

String _moneyLabel(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

String _prettyStatus(String value) => value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word[0].toUpperCase() + word.substring(1))
    .join(' ');

String _timestamp(String value) {
  try {
    return DateFormat('MMM d, h:mm a').format(DateTime.parse(value).toLocal());
  } catch (_) {
    return value;
  }
}

class OrderDetailPage extends ConsumerStatefulWidget {
  final String orderId;

  const OrderDetailPage({super.key, required this.orderId});

  @override
  ConsumerState<OrderDetailPage> createState() => _OrderDetailPageState();
}

class _OrderDetailPageState extends ConsumerState<OrderDetailPage> {
  bool _cancelling = false;

  bool _canCancelOrder(CustomerOrder order) {
    return !{
      'shipped',
      'out_for_delivery',
      'delivered',
      'cancelled',
      'returned',
    }.contains(order.status);
  }

  bool _canRequestReturn(CustomerOrder order) {
    return order.status == 'delivered' &&
        order.items.any((item) => item.status == 'delivered');
  }

  Future<void> _refresh() async {
    await Future.wait([
      ref.refresh(orderDetailProvider(widget.orderId).future),
      ref.refresh(orderTrackingProvider(widget.orderId).future),
    ]);
  }

  Future<void> _cancelOrder(CustomerOrder order) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel order?'),
        content: Text(
          'This will cancel ${order.orderNumber} and stop any remaining fulfilment.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Keep order'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Cancel order'),
          ),
        ],
      ),
    );

    if (confirmed != true) {
      return;
    }

    setState(() => _cancelling = true);
    try {
      await ref.read(commerceRepositoryProvider).cancelOrder(order.id);
      ref.invalidate(ordersProvider);
      ref.invalidate(orderDetailProvider(widget.orderId));
      ref.invalidate(orderTrackingProvider(widget.orderId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Order cancelled'),
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
        setState(() => _cancelling = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final orderAsync = ref.watch(orderDetailProvider(widget.orderId));
    final trackingAsync = ref.watch(orderTrackingProvider(widget.orderId));

    return Scaffold(
      appBar: AppBar(title: const Text('Order Detail')),
      body: orderAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) =>
            Center(child: Text(ErrorHandler.handle(err).message)),
        data: (order) => RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      order.orderNumber,
                      style: Theme.of(
                        context,
                      ).textTheme.headlineMedium?.copyWith(fontSize: 30),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Chip(label: Text(_prettyStatus(order.status))),
                        Chip(label: Text(_prettyStatus(order.paymentStatus))),
                        Chip(label: Text(_moneyLabel(order.total))),
                      ],
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Items',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 10),
                    ...order.items.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    item.productName,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    '${item.variantName} • qty ${item.quantity} • ${_prettyStatus(item.status)}',
                                    style: const TextStyle(
                                      color: AppColors.inkSoft,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text(
                              _moneyLabel(item.totalPrice),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (_canCancelOrder(order) || _canRequestReturn(order)) ...[
                const SizedBox(height: 18),
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
                        'Manage order',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 14),
                      if (_canCancelOrder(order))
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed:
                                _cancelling ? null : () => _cancelOrder(order),
                            icon: _cancelling
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.cancel_outlined),
                            label: const Text('Cancel order'),
                          ),
                        ),
                      if (_canRequestReturn(order)) ...[
                        if (_canCancelOrder(order)) const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.tonalIcon(
                            onPressed: () => context.push(
                              AppConstants.orderReturnRequestRoute(order.id),
                            ),
                            icon: const Icon(Icons.assignment_return_outlined),
                            label: const Text('Request return'),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 18),
              trackingAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, _) => Text(ErrorHandler.handle(err).message),
                data: (tracking) => Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Delivery progress',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 12),
                    ...tracking.shipments.map(
                      (shipment) => Padding(
                        padding: const EdgeInsets.only(bottom: 14),
                        child: Container(
                          padding: const EdgeInsets.all(18),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(28),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                shipment.awb,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${_prettyStatus(shipment.status)} • ${shipment.currentLocation}',
                                style: const TextStyle(
                                  color: AppColors.inkSoft,
                                ),
                              ),
                              const SizedBox(height: 14),
                              ...shipment.events.map(
                                (event) => Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        width: 12,
                                        height: 12,
                                        margin: const EdgeInsets.only(top: 4),
                                        decoration: const BoxDecoration(
                                          color: AppColors.secondary,
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              _prettyStatus(event.status),
                                              style: const TextStyle(
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              '${event.location} • ${event.remarks}',
                                              style: const TextStyle(
                                                color: AppColors.inkSoft,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              _timestamp(event.timestamp),
                                              style: const TextStyle(
                                                fontSize: 12,
                                                color: AppColors.inkSoft,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
