import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/providers/dio_provider.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/loading_button.dart';
import '../providers/auth_provider.dart';
import 'social_auth_webview_page.dart';
import '../widgets/social_provider_buttons.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    await ref
        .read(authNotifierProvider.notifier)
        .login(_usernameController.text.trim(), _passwordController.text);
  }

  Future<void> _socialLogin(String provider) async {
    if (usesNativeGoogleSignIn(provider, isWeb: kIsWeb)) {
      await _nativeGoogleLogin();
      return;
    }

    final result = await Navigator.of(context).push<SocialAuthResult>(
      MaterialPageRoute(
        builder: (_) => SocialAuthWebViewPage(provider: provider),
        fullscreenDialog: true,
      ),
    );
    if (result == null || !result.success) {
      if (result?.error != null && result!.error != 'cancelled' && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Social login failed: ${result.error}'),
            backgroundColor: Colors.red,
          ),
        );
      }
      return;
    }
    final secureStorage = ref.read(secureStorageProvider);
    await secureStorage.saveAccessToken(result.accessToken!);
    await secureStorage.saveRefreshToken(result.refreshToken!);
    await ref.read(authNotifierProvider.notifier).refreshSession(provider: provider);
  }

  Future<void> _nativeGoogleLogin() async {
    try {
      final idToken = await ref
          .read(nativeGoogleSignInServiceProvider)
          .signInAndGetIdToken();

      if (idToken == null) {
        return;
      }

      await ref.read(authNotifierProvider.notifier).loginWithGoogleIdToken(
            idToken,
          );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Google sign-in failed: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);
    final isLoading = authState.isLoading;

    ref.listen(authNotifierProvider, (prev, next) {
      final value = next.valueOrNull;
      if (value == null) return;

      if (value.requiresOtp && value.tempToken != null) {
        context.push(AppConstants.otpVerifyRoute, extra: value.tempToken);
        return;
      }

      final err = value.error;
      if (err != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(err), backgroundColor: Colors.red),
        );
        ref.read(authNotifierProvider.notifier).clearError();
      }
    });

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 40),
                Icon(
                  Icons.lock_outline_rounded,
                  size: 72,
                  color: Theme.of(context).colorScheme.primary,
                ).animate().fadeIn(duration: 500.ms).scale(),
                const SizedBox(height: 24),
                Text(
                  'Welcome back',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                  textAlign: TextAlign.center,
                ).animate().fadeIn(delay: 200.ms),
                const SizedBox(height: 8),
                Text(
                  'Sign in to your account',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: Colors.grey),
                  textAlign: TextAlign.center,
                ).animate().fadeIn(delay: 300.ms),
                const SizedBox(height: 40),
                AppTextField(
                  controller: _usernameController,
                  label: 'Username',
                  prefixIcon: Icons.person_outline,
                  validator: (v) =>
                      v == null || v.isEmpty ? 'Enter your username' : null,
                ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.1),
                const SizedBox(height: 16),
                AppTextField(
                  controller: _passwordController,
                  label: 'Password',
                  prefixIcon: Icons.lock_outline,
                  obscureText: _obscurePassword,
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscurePassword
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                    ),
                    onPressed: () =>
                        setState(() => _obscurePassword = !_obscurePassword),
                  ),
                  validator: (v) =>
                      v == null || v.isEmpty ? 'Enter your password' : null,
                ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.1),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () =>
                        context.push(AppConstants.forgotPasswordRoute),
                    child: const Text('Forgot password?'),
                  ),
                ),
                const SizedBox(height: 16),
                LoadingButton(
                  isLoading: isLoading,
                  onPressed: _login,
                  label: 'Sign In',
                ).animate().fadeIn(delay: 600.ms),
                const SizedBox(height: 24),
                SocialProviderButtons(
                  providersAsync: ref.watch(socialProvidersProvider),
                  onSocialLogin: _socialLogin,
                ),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text("Don't have an account? "),
                    TextButton(
                      onPressed: () => context.go(AppConstants.registerRoute),
                      child: const Text('Sign Up'),
                    ),
                  ],
                ).animate().fadeIn(delay: 700.ms),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
