import 'package:flutter/foundation.dart';
import '../core/config.dart';

class SettingsProvider extends ChangeNotifier {
  AppConfig _config;

  SettingsProvider(this._config);

  AppConfig get config => _config;
  String get apiBaseUrl => _config.apiBaseUrl;

  Future<void> updateApiUrl(String url) async {
    _config = _config.copyWith(apiBaseUrl: url);
    await _config.save();
    notifyListeners();
  }
}
