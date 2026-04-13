import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/loading_button.dart';
import '../../data/models/commerce_models.dart';
import '../providers/commerce_provider.dart';

String _returnStatusLabel(String value) => value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word[0].toUpperCase() + word.substring(1))
    .join(' ');

String _returnDateLabel(String value) {
  try {
    return DateFormat('MMM d, y').format(DateTime.parse(value).toLocal());
  } catch (_) {
    return value;
  }
}

class ReturnRequestPage extends ConsumerStatefulWidget {
  final String orderId;

  const ReturnRequestPage({super.key, required this.orderId});

  @override
  ConsumerState<ReturnRequestPage> createState() => _ReturnRequestPageState();
}

class _ReturnRequestPageState extends ConsumerState<ReturnRequestPage> {
  static const _returnReasons = [
    'Damaged or defective',
    'Wrong item received',
    'Not as described',
    'Quality concerns',
    'Item no longer needed',
    'Other',
  ];

  static const _refundMethods = {
    'original': 'Original payment method',
    'wallet': 'Wallet credit',
  };

  final _formKey = GlobalKey<FormState>();
  final _detailsController = TextEditingController();
  String _selectedReason = _returnReasons.first;
  String _selectedRefundMethod = 'original';
  String? _selectedOrderItemId;
  int _selectedQuantity = 1;
  bool _submitting = false;

  List<CustomerOrderItem> _eligibleItems(CustomerOrder order) {
    return order.items.where((item) => item.status == 'delivered').toList();
  }

  bool _canReturnEntireOrder(CustomerOrder order) {
    final eligibleItems = _eligibleItems(order);
    return eligibleItems.isNotEmpty &&
        eligibleItems.length == order.items.length;
  }

  Future<void> _submitReturn({
    required CustomerOrder order,
    required String? selectedOrderItemId,
    required int selectedQuantity,
  }) async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    setState(() => _submitting = true);
    try {
      final submission =
          await ref.read(commerceRepositoryProvider).createReturnRequest(
                ReturnRequestCreatePayload(
                  orderId: order.id,
                  orderItemId: selectedOrderItemId,
                  quantity: selectedOrderItemId == null ? 1 : selectedQuantity,
                  reason: _selectedReason,
                  details: _detailsController.text.trim(),
                  refundMethod: _selectedRefundMethod,
                ),
              );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Return request submitted'),
          backgroundColor: AppColors.success,
        ),
      );
      context.pushReplacement(
        AppConstants.returnRequestRoute(submission.returnRequestId),
      );
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
        setState(() => _submitting = false);
      }
    }
  }

  @override
  void dispose() {
    _detailsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final orderAsync = ref.watch(orderDetailProvider(widget.orderId));

    return Scaffold(
      appBar: AppBar(title: const Text('Request Return')),
      body: orderAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(ErrorHandler.handle(err).message),
          ),
        ),
        data: (order) {
          final eligibleItems = _eligibleItems(order);

          if (order.status != 'delivered' || eligibleItems.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.assignment_return_outlined,
                      size: 52,
                      color: AppColors.inkSoft,
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Returns are only available for delivered items while the backend return window is still open.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton(
                      onPressed: () =>
                          context.go(AppConstants.orderDetailRoute(order.id)),
                      child: const Text('Back to order'),
                    ),
                  ],
                ),
              ),
            );
          }

          final canReturnEntireOrder = _canReturnEntireOrder(order);
          final selectedOrderItemId = canReturnEntireOrder
              ? _selectedOrderItemId
              : (_selectedOrderItemId ?? eligibleItems.first.id);
          final selectedItem = selectedOrderItemId == null
              ? null
              : eligibleItems.firstWhere(
                  (item) => item.id == selectedOrderItemId,
                  orElse: () => eligibleItems.first,
                );
          final selectedQuantity = selectedItem == null
              ? 1
              : (_selectedQuantity > selectedItem.quantity
                  ? selectedItem.quantity
                  : _selectedQuantity);

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      order.orderNumber,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '${_returnStatusLabel(order.status)} • placed ${_returnDateLabel(order.createdAt)}',
                      style: const TextStyle(color: AppColors.inkSoft),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Submit one request per item when only part of the order has been delivered.',
                      style: TextStyle(color: AppColors.inkSoft, height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Return details',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String?>(
                        key: ValueKey(
                          'return-target-${selectedOrderItemId ?? 'order'}-${eligibleItems.length}',
                        ),
                        initialValue: canReturnEntireOrder
                            ? _selectedOrderItemId
                            : selectedOrderItemId,
                        decoration: const InputDecoration(
                          labelText: 'What are you returning?',
                        ),
                        items: [
                          if (canReturnEntireOrder)
                            const DropdownMenuItem<String?>(
                              value: null,
                              child: Text('Entire delivered order'),
                            ),
                          ...eligibleItems.map(
                            (item) => DropdownMenuItem<String?>(
                              value: item.id,
                              child: Text(
                                '${item.productName} • ${item.variantName}',
                              ),
                            ),
                          ),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _selectedOrderItemId = value;
                            _selectedQuantity = 1;
                          });
                        },
                      ),
                      const SizedBox(height: 16),
                      if (selectedItem != null) ...[
                        DropdownButtonFormField<int>(
                          key: ValueKey(
                            'return-quantity-${selectedOrderItemId ?? 'order'}',
                          ),
                          initialValue: selectedQuantity,
                          decoration: const InputDecoration(
                            labelText: 'Quantity',
                          ),
                          items: List.generate(
                            selectedItem.quantity,
                            (index) => DropdownMenuItem<int>(
                              value: index + 1,
                              child: Text('${index + 1}'),
                            ),
                          ),
                          onChanged: (value) => setState(
                            () => _selectedQuantity = value ?? 1,
                          ),
                        ),
                        const SizedBox(height: 16),
                      ] else ...[
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceWarm,
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: const Text(
                            'The backend will calculate the full remaining eligible quantity for this order-level return.',
                            style: TextStyle(color: AppColors.inkSoft),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                      DropdownButtonFormField<String>(
                        initialValue: _selectedReason,
                        decoration: const InputDecoration(
                          labelText: 'Reason',
                        ),
                        items: _returnReasons
                            .map(
                              (reason) => DropdownMenuItem<String>(
                                value: reason,
                                child: Text(reason),
                              ),
                            )
                            .toList(),
                        onChanged: (value) => setState(
                          () => _selectedReason = value ?? _returnReasons.first,
                        ),
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        initialValue: _selectedRefundMethod,
                        decoration: const InputDecoration(
                          labelText: 'Refund method',
                        ),
                        items: _refundMethods.entries
                            .map(
                              (entry) => DropdownMenuItem<String>(
                                value: entry.key,
                                child: Text(entry.value),
                              ),
                            )
                            .toList(),
                        onChanged: (value) => setState(
                          () => _selectedRefundMethod = value ?? 'original',
                        ),
                      ),
                      const SizedBox(height: 16),
                      AppTextField(
                        controller: _detailsController,
                        label: 'Details (optional)',
                        prefixIcon: Icons.notes_outlined,
                        maxLines: 4,
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: LoadingButton(
                          isLoading: _submitting,
                          onPressed: () => _submitReturn(
                            order: order,
                            selectedOrderItemId: selectedOrderItemId,
                            selectedQuantity: selectedQuantity,
                          ),
                          label: 'Submit return request',
                          icon: Icons.assignment_return_outlined,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
