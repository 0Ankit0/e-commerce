import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:google_sign_in/google_sign_in.dart';

class NativeGoogleSignInService {
  GoogleSignIn _client() {
    final serverClientId = dotenv.env['GOOGLE_SERVER_CLIENT_ID']?.trim();
    return GoogleSignIn(
      scopes: const ['email', 'profile'],
      serverClientId: serverClientId != null && serverClientId.isNotEmpty
          ? serverClientId
          : null,
    );
  }

  Future<String?> signInAndGetIdToken() async {
    final serverClientId = dotenv.env['GOOGLE_SERVER_CLIENT_ID']?.trim();
    if (serverClientId == null || serverClientId.isEmpty) {
      throw StateError(
        'GOOGLE_SERVER_CLIENT_ID is not configured for native Google sign-in.',
      );
    }

    final googleSignIn = _client();
    try {
      await googleSignIn.signOut();
      final account = await googleSignIn.signIn();
      if (account == null) {
        return null;
      }

      final authentication = await account.authentication;
      final idToken = authentication.idToken;
      if (idToken == null || idToken.isEmpty) {
        throw StateError(
          'Google sign-in completed, but no ID token was returned. Check GOOGLE_SERVER_CLIENT_ID and your platform OAuth configuration.',
        );
      }
      return idToken;
    } finally {
      try {
        await googleSignIn.disconnect();
      } catch (_) {
        await googleSignIn.signOut();
      }
    }
  }
}
