import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:mobile/core/network/dio_client.dart';
import 'package:mobile/core/storage/secure_storage.dart';
import 'package:mobile/features/auth/data/repositories/auth_repository.dart';
import 'package:mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:mobile/features/auth/presentation/widgets/social_provider_buttons.dart';

class _FakeSecureStorage extends SecureStorage {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<String?> getRefreshToken() async => null;

  @override
  Future<void> saveAccessToken(String token) async {}

  @override
  Future<void> saveRefreshToken(String token) async {}

  @override
  Future<void> clearTokens() async {}
}

class _FakeDioClient extends DioClient {
  _FakeDioClient() : super(_FakeSecureStorage());
}

class _FakeAuthRepository extends AuthRepository {
  final List<String> providers;

  _FakeAuthRepository(this.providers) : super(_FakeDioClient());

  @override
  Future<List<String>> getEnabledSocialProviders() async => providers;
}

void main() {
  setUpAll(() {
    dotenv.testLoad(fileInput: 'BASE_URL=http://127.0.0.1:8000/api/v1');
  });

  test('social providers include apple when the backend exposes it', () async {
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(
          _FakeAuthRepository(['google', 'apple']),
        ),
      ],
    );
    addTearDown(container.dispose);

    final providers = await container.read(socialProvidersProvider.future);
    expect(providers, contains('apple'));
  });

  testWidgets('social provider buttons render Apple when enabled', (tester) async {
    String? tappedProvider;

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: SocialProviderButtons(
              providersAsync: const AsyncValue.data(['apple']),
              onSocialLogin: (provider) async {
                tappedProvider = provider;
              },
            ),
          ),
        ),
      ),
    );

    expect(find.text('Apple'), findsOneWidget);

    await tester.tap(find.text('Apple'));
    await tester.pump();

    expect(tappedProvider, 'apple');
  });

  test('apple stays on the shared webview social-login flow', () {
    expect(socialProviderLabel('apple'), 'Apple');
    expect(usesNativeGoogleSignIn('apple', isWeb: false), isFalse);
    expect(usesNativeGoogleSignIn('google', isWeb: false), isTrue);
  });
}
