import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

class ApiClient {
  final String baseUrl;
  String? _authToken;

  ApiClient(this.baseUrl);

  void setToken(String token) => _authToken = token;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_authToken != null) 'Authorization': 'Bearer $_authToken',
  };

  // ===== REST =====

  Future<Map<String, dynamic>> chat({
    required List<Map<String, String>> messages,
    String? sessionId,
    double temperature = 0.7,
  }) async {
    final resp = await http.post(
      Uri.parse('$baseUrl/api/v1/chat'),
      headers: _headers,
      body: jsonEncode({
        'messages': messages,
        if (sessionId != null) 'session_id': sessionId,
        'temperature': temperature,
      }),
    );
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }
    throw Exception('Chat error: ${resp.statusCode} ${resp.body}');
  }

  Future<List<dynamic>> getAgents() async {
    final resp = await http.get(
      Uri.parse('$baseUrl/api/v1/agents'),
      headers: _headers,
    );
    if (resp.statusCode == 200) return jsonDecode(resp.body) as List;
    throw Exception('Agents error: ${resp.statusCode}');
  }

  Future<bool> checkHealth() async {
    try {
      final resp = await http.get(
        Uri.parse('$baseUrl/health'),
        headers: _headers,
      ).timeout(const Duration(seconds: 5));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ===== WebSocket Streaming =====

  WebSocketChannel connectStream(String sessionId) {
    final wsUrl = baseUrl
        .replaceFirst('http://', 'ws://')
        .replaceFirst('https://', 'wss://');
    return WebSocketChannel.connect(
      Uri.parse('$wsUrl/ws/chat/$sessionId'),
    );
  }
}
