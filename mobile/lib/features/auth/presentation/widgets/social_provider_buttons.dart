import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

String socialProviderLabel(String provider) {
  switch (provider) {
    case 'google':
      return 'Google';
    case 'github':
      return 'GitHub';
    case 'facebook':
      return 'Facebook';
    case 'apple':
      return 'Apple';
    default:
      return provider.isEmpty
          ? 'Provider'
          : provider[0].toUpperCase() + provider.substring(1);
  }
}

bool usesNativeGoogleSignIn(String provider, {required bool isWeb}) {
  return provider == 'google' && !isWeb;
}

class SocialProviderButtons extends ConsumerWidget {
  final AsyncValue<List<String>> providersAsync;
  final Future<void> Function(String provider) onSocialLogin;

  const SocialProviderButtons({
    super.key,
    required this.providersAsync,
    required this.onSocialLogin,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return providersAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (providers) {
        if (providers.isEmpty) return const SizedBox.shrink();
        return Column(
          children: [
            Row(
              children: [
                const Expanded(child: Divider()),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text(
                    'Or continue with',
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.grey),
                  ),
                ),
                const Expanded(child: Divider()),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: providers.map((provider) {
                return Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: OutlinedButton(
                      onPressed: () => onSocialLogin(provider),
                      child: Text(socialProviderLabel(provider)),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        );
      },
    );
  }
}
