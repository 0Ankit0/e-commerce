import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../data/models/commerce_models.dart';
import '../providers/commerce_provider.dart';

String _returnDetailLabel(String value) => value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word[0].toUpperCase() + word.substring(1))
    .join(' ');

String _returnDetailDate(String value) {
  try {
    return DateFormat('MMM d, y • h:mm a')
        .format(DateTime.parse(value).toLocal());
  } catch (_) {
    return value;
  }
}

Color _returnStatusColor(String status) {
  switch (status) {
    case 'approved':
    case 'received':
      return Colors.blue;
    case 'refunded':
      return AppColors.success;
    case 'rejected':
      return Colors.red;
    case 'reverse_pickup_assigned':
    case 'picked_up':
      return Colors.deepPurple;
    default:
      return Colors.orange;
  }
}

String _refundMethodLabel(String value) {
  switch (value) {
    case 'wallet':
      return 'Wallet credit';
    case 'original':
      return 'Original payment method';
    default:
      return _returnDetailLabel(value);
  }
}

class ReturnRequestDetailPage extends ConsumerWidget {
  final String returnRequestId;

  const ReturnRequestDetailPage({super.key, required this.returnRequestId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final returnRequestAsync =
        ref.watch(returnRequestProvider(returnRequestId));

    return Scaffold(
      appBar: AppBar(title: const Text('Return Request')),
      body: returnRequestAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(ErrorHandler.handle(err).message),
          ),
        ),
        data: (returnRequest) {
          final timelineAsync = ref.watch(
            returnRequestTimelineProvider(returnRequestId),
          );
          final orderAsync =
              ref.watch(orderDetailProvider(returnRequest.orderId));
          final statusColor = _returnStatusColor(returnRequest.status);

          return RefreshIndicator(
            onRefresh: () async {
              await Future.wait([
                ref.refresh(returnRequestProvider(returnRequestId).future),
                ref.refresh(
                  returnRequestTimelineProvider(returnRequestId).future,
                ),
              ]);
            },
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
                        'Return ${returnRequest.id}',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: Text(
                          _returnDetailLabel(returnRequest.status),
                          style: TextStyle(
                            color: statusColor,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        returnRequest.reason,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Requested ${_returnDetailDate(returnRequest.createdAt)}',
                        style: const TextStyle(color: AppColors.inkSoft),
                      ),
                      if (orderAsync.valueOrNull != null) ...[
                        const SizedBox(height: 16),
                        FilledButton.tonalIcon(
                          onPressed: () => context.push(
                            AppConstants.orderDetailRoute(
                                returnRequest.orderId),
                          ),
                          icon: const Icon(Icons.receipt_long_outlined),
                          label: Text(
                            'Open ${orderAsync.valueOrNull!.orderNumber}',
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(30),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Request summary',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 14),
                      _DetailRow(
                        label: 'Refund method',
                        value: _refundMethodLabel(returnRequest.refundMethod),
                      ),
                      const SizedBox(height: 10),
                      _DetailRow(
                        label: 'Quantity',
                        value: '${returnRequest.quantity}',
                      ),
                      const SizedBox(height: 10),
                      _DetailRow(
                        label: 'Eligible until',
                        value: returnRequest.eligibleUntil == null
                            ? '—'
                            : _returnDetailDate(returnRequest.eligibleUntil!),
                      ),
                      if (returnRequest.resolvedAt != null) ...[
                        const SizedBox(height: 10),
                        _DetailRow(
                          label: 'Resolved',
                          value: _returnDetailDate(returnRequest.resolvedAt!),
                        ),
                      ],
                      if (returnRequest.details.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        const Text(
                          'Details',
                          style: TextStyle(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          returnRequest.details,
                          style: const TextStyle(
                            color: AppColors.inkSoft,
                            height: 1.5,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                const Text(
                  'Timeline',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                timelineAsync.when(
                  loading: () => const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: CircularProgressIndicator(),
                    ),
                  ),
                  error: (err, _) => Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(ErrorHandler.handle(err).message),
                  ),
                  data: (events) {
                    if (events.isEmpty) {
                      return Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(28),
                        ),
                        child: const Text(
                          'No timeline updates are available yet.',
                          style: TextStyle(color: AppColors.inkSoft),
                        ),
                      );
                    }

                    return Column(
                      children: events
                          .map(
                            (event) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _TimelineCard(event: event),
                            ),
                          )
                          .toList(),
                    );
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 110,
          child: Text(
            label,
            style: const TextStyle(color: AppColors.inkSoft),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _TimelineCard extends StatelessWidget {
  final ReturnTimelineEvent event;

  const _TimelineCard({required this.event});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 12,
            height: 12,
            margin: const EdgeInsets.only(top: 6),
            decoration: const BoxDecoration(
              color: AppColors.secondary,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  event.message.isNotEmpty
                      ? event.message
                      : _returnDetailLabel(event.eventType),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  _returnDetailDate(event.createdAt),
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
    );
  }
}
