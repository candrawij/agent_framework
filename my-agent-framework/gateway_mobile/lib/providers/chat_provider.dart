import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../core/api_client.dart';
import '../models/chat_message.dart';

class ChatProvider extends ChangeNotifier {
  ApiClient _client;
  final List<ChatMessage> _messages = [];
  String? _sessionId;
  bool _isLoading = false;
  String? _error;

  ChatProvider(this._client);

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;
  String? get error => _error;
  String? get sessionId => _sessionId;

  void updateClient(ApiClient client) {
    _client = client;
  }

  Future<void> sendMessage(String content) async {
    if (content.trim().isEmpty) return;

    // Add user message
    final userMsg = ChatMessage.user(content);
    _messages.add(userMsg);
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      // Add placeholder assistant message
      final assistantMsg = ChatMessage.assistant('', isStreaming: true);
      _messages.add(assistantMsg);
      
      final response = await _client.chat(
        messages: _messages
            .where((m) => m.role == MessageRole.user || m.role == MessageRole.assistant)
            .where((m) => !m.isStreaming)
            .map((m) => m.toApiMap())
            .toList(),
        sessionId: _sessionId,
      );

      _sessionId = response['session_id'] as String?;
      final responseContent = response['content'] as String? ?? '';

      // Update assistant message
      final idx = _messages.indexOf(assistantMsg);
      if (idx >= 0) {
        _messages[idx] = assistantMsg.copyWith(
          content: responseContent,
          isStreaming: false,
        );
      }

    } catch (e) {
      _error = e.toString();
      // Remove placeholder if error
      _messages.removeWhere((m) => m.isStreaming);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearSession() {
    _messages.clear();
    _sessionId = null;
    _error = null;
    notifyListeners();
  }
}
