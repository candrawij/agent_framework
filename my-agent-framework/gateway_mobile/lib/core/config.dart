import 'package:shared_preferences/shared_preferences.dart';

class AppConfig {
  final String apiBaseUrl;
  final String wsBaseUrl;
  final String? authToken;

  const AppConfig({
    required this.apiBaseUrl,
    required this.wsBaseUrl,
    this.authToken,
  });

  static const String _defaultApiUrl = 'http://localhost:8000';
  static const String _defaultWsUrl = 'ws://localhost:8000';

  static Future<AppConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    return AppConfig(
      apiBaseUrl: prefs.getString('api_url') ?? _defaultApiUrl,
      wsBaseUrl: prefs.getString('ws_url') ?? _defaultWsUrl,
      authToken: prefs.getString('auth_token'),
    );
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_url', apiBaseUrl);
    await prefs.setString('ws_url', wsBaseUrl);
    if (authToken != null) {
      await prefs.setString('auth_token', authToken!);
    }
  }

  AppConfig copyWith({String? apiBaseUrl, String? wsBaseUrl, String? authToken}) {
    return AppConfig(
      apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
      wsBaseUrl: wsBaseUrl ?? this.wsBaseUrl,
      authToken: authToken ?? this.authToken,
    );
  }
}
