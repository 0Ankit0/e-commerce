class AppConstants {
  AppConstants._();

  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';

  // Route names
  static const String loginRoute = '/login';
  static const String registerRoute = '/register';
  static const String forgotPasswordRoute = '/forgot-password';
  static const String otpVerifyRoute = '/otp-verify';
  static const String resetPasswordRoute = '/reset-password';
  static const String homeRoute = '/home';
  static const String ordersRoute = '/home/orders';
  static const String notificationsRoute = '/home/notifications';
  static const String profileRoute = '/home/profile';
  static const String settingsRoute = '/home/profile/settings';
  static const String tokensRoute = '/home/profile/settings/tokens';
  static const String cartRoute = '/home/cart';
  static const String checkoutRoute = '/home/checkout';

  static String productRoute(String productId) => '/home/products/$productId';
  static String orderDetailRoute(String orderId) => '/home/orders/$orderId';

  // Social auth — the backend redirects here after OAuth; the WebView intercepts it
  static const String socialAuthCallbackPrefix = '/auth-callback';
}
