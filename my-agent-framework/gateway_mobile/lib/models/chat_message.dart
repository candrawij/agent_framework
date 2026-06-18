enum MessageRole { user, assistant, system, tool }

class ChatMessage {
  final String id;
  final MessageRole role;
  final String content;
  final DateTime timestamp;
  final bool isStreaming;

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.timestamp,
    this.isStreaming = false,
  });

  ChatMessage copyWith({
    String? content,
    bool? isStreaming,
  }) {
    return ChatMessage(
      id: id,
      role: role,
      content: content ?? this.content,
      timestamp: timestamp,
      isStreaming: isStreaming ?? this.isStreaming,
    );
  }

  Map<String, String> toApiMap() => {
    'role': role.name,
    'content': content,
  };

  factory ChatMessage.user(String content) => ChatMessage(
    id: DateTime.now().microsecondsSinceEpoch.toString(),
    role: MessageRole.user,
    content: content,
    timestamp: DateTime.now(),
  );

  factory ChatMessage.assistant(String content, {bool isStreaming = false}) =>
      ChatMessage(
    id: DateTime.now().microsecondsSinceEpoch.toString(),
    role: MessageRole.assistant,
    content: content,
    timestamp: DateTime.now(),
    isStreaming: isStreaming,
  );
}
