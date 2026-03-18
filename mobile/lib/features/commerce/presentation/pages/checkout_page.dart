import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../payments/data/models/payment.dart';
import '../../../payments/presentation/pages/payment_webview_page.dart';
import '../../../payments/presentation/providers/payment_provider.dart';
import '../../data/models/commerce_models.dart';
import '../providers/commerce_provider.dart';

String _price(num value) =>
    NumberFormat.currency(symbol: '\$', decimalDigits: 2).format(value);

class CheckoutPage extends ConsumerStatefulWidget {
  const CheckoutPage({super.key});

  @override
  ConsumerState<CheckoutPage> createState() => _CheckoutPageState();
}

class _CheckoutPageState extends ConsumerState<CheckoutPage> {
  static const _corePaymentOptions = [
    ('cod', 'Cash on delivery', 'Ready in the mobile UI now.'),
    ('wallet', 'Wallet', 'Ready in the mobile UI now.'),
  ];
  static const _gatewayLabels = {
    'khalti': ('Khalti', 'Shown only when Khalti is enabled in the backend.'),
    'esewa': ('eSewa', 'Shown only when eSewa is enabled in the backend.'),
  };
  String _selectedAddressId = '';
  String _paymentMethod = 'cod';
  String _notes = '';
  bool _submitting = false;
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _line1Controller = TextEditingController();
  final _line2Controller = TextEditingController();
  final _cityController = TextEditingController();
  final _stateController = TextEditingController();
  final _pincodeController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _line1Controller.dispose();
    _line2Controller.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _pincodeController.dispose();
    super.dispose();
  }

  Future<void> _saveAddress() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      final address = await ref.read(commerceRepositoryProvider).createAddress({
        'name': _nameController.text.trim(),
        'phone': _phoneController.text.trim(),
        'line1': _line1Controller.text.trim(),
        'line2': _line2Controller.text.trim(),
        'city': _cityController.text.trim(),
        'state': _stateController.text.trim(),
        'pincode': _pincodeController.text.trim(),
        'country': 'Nepal',
        'landmark': '',
        'type': 'home',
        'is_default': false,
      });
      ref.invalidate(addressesProvider);
      setState(() => _selectedAddressId = address.id);
      _formKey.currentState!.reset();
      _nameController.clear();
      _phoneController.clear();
      _line1Controller.clear();
      _line2Controller.clear();
      _cityController.clear();
      _stateController.clear();
      _pincodeController.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Address added'),
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
    }
  }

  Future<void> _placeOrder(CheckoutQuote quote) async {
    if (_selectedAddressId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select a delivery address first.')),
      );
      return;
    }

    if (!quote.shipping.serviceable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'This address is not currently serviceable. Pick another one before placing the order.',
          ),
        ),
      );
      return;
    }

    setState(() => _submitting = true);
    try {
      String? paymentTransactionId;

      if (_paymentMethod == 'khalti' || _paymentMethod == 'esewa') {
        final provider = PaymentProvider.fromString(_paymentMethod);
        final authUser = ref.read(authNotifierProvider).valueOrNull?.user;
        final purchaseOrderId = 'CHK-${DateTime.now().millisecondsSinceEpoch}';
        final paymentRepository = ref.read(paymentRepositoryProvider);
        final providerContainer = ProviderScope.containerOf(context);
        final navigator = Navigator.of(context);
        final initiated = await paymentRepository.initiatePayment(
          InitiatePaymentRequest(
            provider: provider,
            amount: provider == PaymentProvider.khalti
                ? (quote.total * 100).round()
                : quote.total.round(),
            purchaseOrderId: purchaseOrderId,
            purchaseOrderName: 'Checkout $purchaseOrderId',
            returnUrl:
                'http://localhost:3000/payment-callback?provider=${provider.name}',
            websiteUrl: 'http://localhost:3000',
            customerName: authUser?.displayName,
            customerEmail: authUser?.email,
            customerPhone: authUser?.phone,
          ),
        );

        final paymentResult = await navigator.push<PaymentResult>(
          MaterialPageRoute(
            fullscreenDialog: true,
            builder: (_) => UncontrolledProviderScope(
              container: providerContainer,
              child: PaymentWebViewPage(
                provider: initiated.provider,
                paymentUrl: initiated.paymentUrl,
                esewaFormAction: initiated.extra?['form_action'] as String?,
                esewaFormFields: initiated.extra?['form_fields'] is Map
                    ? Map<String, dynamic>.from(
                        initiated.extra!['form_fields'] as Map,
                      )
                    : null,
              ),
            ),
          ),
        );

        if (!mounted) {
          return;
        }

        if (paymentResult == null ||
            !paymentResult.success ||
            paymentResult.response == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                paymentResult?.message ?? 'Payment was not completed.',
              ),
              backgroundColor: Colors.red,
            ),
          );
          return;
        }

        paymentTransactionId = paymentResult.response!.transactionId;
      }

      final order = await ref.read(commerceRepositoryProvider).checkout(
            addressId: _selectedAddressId,
            paymentMethod: _paymentMethod,
            quoteFingerprint: quote.fingerprint,
            paymentTransactionId: paymentTransactionId,
            notes: _notes,
          );
      ref.invalidate(cartProvider);
      ref.invalidate(ordersProvider);
      ref.invalidate(transactionsProvider);
      if (mounted) {
        context.go(AppConstants.orderDetailRoute(order.id));
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

  @override
  Widget build(BuildContext context) {
    final addressesAsync = ref.watch(addressesProvider);
    final cartAsync = ref.watch(cartProvider);
    final paymentProvidersAsync = ref.watch(paymentProvidersProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Checkout')),
      body: addressesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) =>
            Center(child: Text(ErrorHandler.handle(err).message)),
        data: (addresses) {
          if (_selectedAddressId.isEmpty && addresses.isNotEmpty) {
            _selectedAddressId = addresses
                .firstWhere(
                  (address) => address.isDefault,
                  orElse: () => addresses.first,
                )
                .id;
          }
          final selectedAddressId = _selectedAddressId;
          final quoteAsync = selectedAddressId.isEmpty
              ? const AsyncValue<CheckoutQuote>.loading()
              : ref.watch(
                  checkoutQuoteProvider((
                    addressId: selectedAddressId,
                    paymentMethod: _paymentMethod,
                  )),
                );
          final enabledGatewayOptions = (paymentProvidersAsync.valueOrNull ??
                  const <String>[])
              .where((provider) => provider == 'khalti' || provider == 'esewa')
              .map((provider) {
            final label = _gatewayLabels[provider]!;
            return (provider, label.$1, label.$2);
          }).toList();
          final paymentOptions = [
            ..._corePaymentOptions,
            ...enabledGatewayOptions
          ];

          if (!paymentOptions.any((option) => option.$1 == _paymentMethod)) {
            _paymentMethod = 'cod';
          }

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              const Text(
                'Delivery address',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              ...addresses.map(
                (address) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _SelectableTile(
                    selected: selectedAddressId == address.id,
                    title: address.name,
                    subtitle: address.compactLabel,
                    onTap: () =>
                        setState(() => _selectedAddressId = address.id),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              ExpansionTile(
                collapsedShape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                backgroundColor: Colors.white,
                collapsedBackgroundColor: Colors.white,
                title: const Text('Add new address'),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  Form(
                    key: _formKey,
                    child: Column(
                      children: [
                        TextFormField(
                          controller: _nameController,
                          decoration: const InputDecoration(
                            labelText: 'Full name',
                          ),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Required'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _phoneController,
                          decoration: const InputDecoration(labelText: 'Phone'),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Required'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _line1Controller,
                          decoration: const InputDecoration(
                            labelText: 'Address line 1',
                          ),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Required'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _line2Controller,
                          decoration: const InputDecoration(
                            labelText: 'Address line 2',
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _cityController,
                          decoration: const InputDecoration(labelText: 'City'),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Required'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _stateController,
                          decoration: const InputDecoration(labelText: 'State'),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Required'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _pincodeController,
                          decoration: const InputDecoration(
                            labelText: 'Pincode',
                          ),
                          validator: (value) => value == null || value.isEmpty
                              ? 'Required'
                              : null,
                        ),
                        const SizedBox(height: 16),
                        FilledButton(
                          onPressed: _saveAddress,
                          child: const Text('Save address'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const Text(
                'Payment',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              ...paymentOptions.map(
                (option) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _SelectableTile(
                    selected: _paymentMethod == option.$1,
                    title: option.$2,
                    subtitle: option.$3,
                    onTap: () => setState(() => _paymentMethod = option.$1),
                  ),
                ),
              ),
              if (enabledGatewayOptions.isEmpty)
                Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: AppColors.primary.withValues(alpha: 0.08),
                    ),
                  ),
                  child: const Text(
                    'No online gateway is enabled by the backend right now, so checkout only shows COD and wallet.',
                    style: TextStyle(color: AppColors.inkSoft),
                  ),
                ),
              const SizedBox(height: 4),
              TextField(
                onChanged: (value) => _notes = value,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Delivery notes',
                  hintText: 'Apartment, landmark, or delivery instructions',
                ),
              ),
              const SizedBox(height: 20),
              cartAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, _) => Text(ErrorHandler.handle(err).message),
                data: (cart) => quoteAsync.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (err, _) => Text(ErrorHandler.handle(err).message),
                  data: (quote) => Container(
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
                        _CheckoutRow(
                          label: 'Items',
                          value: '${cart.totalQuantity}',
                        ),
                        _CheckoutRow(
                          label: 'Subtotal',
                          value: _price(quote.cart.subtotal),
                        ),
                        _CheckoutRow(
                          label: 'Discount',
                          value: '- ${_price(quote.cart.discount)}',
                        ),
                        _CheckoutRow(
                          label: 'Shipping',
                          value: _price(quote.shipping.shippingRate),
                        ),
                        _CheckoutRow(label: 'Tax', value: _price(quote.tax)),
                        const Divider(height: 26),
                        _CheckoutRow(
                          label: 'Total',
                          value: _price(quote.total),
                          emphasize: true,
                        ),
                        const SizedBox(height: 16),
                        FilledButton(
                          onPressed:
                              _submitting ? null : () => _placeOrder(quote),
                          child: Text(
                            _submitting ? 'Placing order...' : 'Place order',
                          ),
                        ),
                      ],
                    ),
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

class _CheckoutRow extends StatelessWidget {
  final String label;
  final String value;
  final bool emphasize;

  const _CheckoutRow({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      fontWeight: emphasize ? FontWeight.w700 : FontWeight.w500,
      fontSize: emphasize ? 16 : 14,
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: style),
          Text(value, style: style),
        ],
      ),
    );
  }
}

class _SelectableTile extends StatelessWidget {
  final bool selected;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _SelectableTile({
    required this.selected,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: Ink(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: selected
                ? AppColors.primary
                : AppColors.primary.withValues(alpha: 0.08),
            width: selected ? 1.4 : 1,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(
                selected
                    ? Icons.radio_button_checked_rounded
                    : Icons.radio_button_off_rounded,
                color: selected ? AppColors.secondary : AppColors.inkSoft,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Text(subtitle,
                        style: const TextStyle(color: AppColors.inkSoft)),
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
