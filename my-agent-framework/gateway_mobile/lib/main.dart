import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';

import 'core/config.dart';
import 'core/api_client.dart';
import 'providers/chat_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/chat_screen.dart';
import 'screens/settings_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final config = await AppConfig.load();
  
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => SettingsProvider(config)),
        ProxyProvider<SettingsProvider, ApiClient>(
          update: (_, settings, __) => ApiClient(settings.apiBaseUrl),
        ),
        ChangeNotifierProxyProvider<ApiClient, ChatProvider>(
          create: (_) => ChatProvider(ApiClient(config.apiBaseUrl)),
          update: (_, client, prev) => prev?..updateClient(client) ?? ChatProvider(client),
        ),
      ],
      child: const AgentFrameworkApp(),
    ),
  );
}

class AgentFrameworkApp extends StatelessWidget {
  const AgentFrameworkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agent Framework',
      debugShowCheckedModeBanner: false,
      theme: _buildTheme(Brightness.dark),
      initialRoute: '/',
      routes: {
        '/': (ctx) => const ChatScreen(),
        '/settings': (ctx) => const SettingsScreen(),
      },
    );
  }

  ThemeData _buildTheme(Brightness brightness) {
    final base = ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF6C63FF),
        brightness: brightness,
      ),
      useMaterial3: true,
    );
    return base.copyWith(
      textTheme: GoogleFonts.interTextTheme(base.textTheme),
    );
  }
}
