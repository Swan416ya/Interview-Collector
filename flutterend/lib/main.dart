import 'dart:convert';

import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

void main() {
  runApp(const InterviewCollectorApp());
}

class InterviewCollectorApp extends StatelessWidget {
  const InterviewCollectorApp({super.key});

  @override
  Widget build(BuildContext context) {
    final baseText = GoogleFonts.notoSansScTextTheme();
    final colorScheme = FlexSchemeColor.from(
      primary: const Color(0xFF7B61FF),
      primaryContainer: const Color(0xFFE8DEFF),
      secondary: const Color(0xFF7E71CF),
      secondaryContainer: const Color(0xFFECE7FF),
      tertiary: const Color(0xFF9E77ED),
      tertiaryContainer: const Color(0xFFF1E9FF),
      appBarColor: const Color(0xFFF8F6FF),
    );
    return MaterialApp(
      title: 'Interview Collector',
      debugShowCheckedModeBanner: false,
      theme: FlexThemeData.light(
        useMaterial3: true,
        colors: colorScheme,
        scaffoldBackground: const Color(0xFFF6F5FA),
        surfaceMode: FlexSurfaceMode.levelSurfacesLowScaffold,
        blendLevel: 10,
        subThemesData: const FlexSubThemesData(
          defaultRadius: 24,
          cardRadius: 28,
          inputDecoratorRadius: 24,
          navigationBarHeight: 74,
          navigationBarMutedUnselectedLabel: true,
          filledButtonRadius: 20,
          outlinedButtonRadius: 20,
          segmentedButtonRadius: 18,
        ),
        textTheme: baseText,
      ).copyWith(
        textTheme: baseText,
        cardTheme: const CardTheme(
          elevation: 0,
          margin: EdgeInsets.zero,
          color: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(28))),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(22),
            borderSide: BorderSide.none,
          ),
        ),
      ),
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;
  final _api = ApiClient(baseUrl: apiBaseUrl);

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeTab(api: _api),
      QuestionsTab(api: _api),
      PracticeTab(api: _api),
    ];
    return Scaffold(
      body: pages[_index],
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(14, 0, 14, 10),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(24),
          child: NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: (v) => setState(() => _index = v),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: '首页'),
              NavigationDestination(
                icon: Icon(Icons.menu_book_outlined),
                selectedIcon: Icon(Icons.menu_book),
                label: '题库',
              ),
              NavigationDestination(
                icon: Icon(Icons.psychology_alt_outlined),
                selectedIcon: Icon(Icons.psychology_alt),
                label: '练习',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class HomeTab extends StatefulWidget {
  const HomeTab({super.key, required this.api});
  final ApiClient api;

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  bool loading = true;
  String? error;
  int total = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final page = await widget.api.fetchQuestionsPage(page: 1, pageSize: 1);
      if (!mounted) return;
      setState(() => total = page.total);
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              clipBehavior: Clip.antiAlias,
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: const BoxDecoration(
                  gradient: LinearGradient(colors: [Color(0xFF8D73FF), Color(0xFF6D4DFF)]),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Interview Collector', style: TextStyle(color: Colors.white, fontSize: 24)),
                    SizedBox(height: 8),
                    Text('API: $apiBaseUrl', style: TextStyle(color: Colors.white70)),
                  ],
                ),
              ),
            ).animate().fadeIn(duration: 320.ms).slideY(begin: 0.08, end: 0),
            const SizedBox(height: 16),
            if (loading)
              const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
            else if (error != null)
              Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error))
            else
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _StatCard(title: '题目总数', value: '$total'),
                  const _StatCard(title: '当前阶段', value: '本地联调'),
                ],
              ),
            const SizedBox(height: 16),
            const Card(
              color: Color(0xFFEFEBFF),
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('使用提示', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                    SizedBox(height: 8),
                    Text('1. Android 模拟器请用 10.0.2.2 访问本机后端。'),
                    Text('2. 真机调试请把 API_BASE_URL 改成你电脑局域网 IP。'),
                    Text('3. 题库与练习页都支持下拉刷新。'),
                  ],
                ),
              ),
            ).animate().fadeIn(delay: 120.ms, duration: 280.ms),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.title, required this.value});
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 170,
      child: Card(
        color: const Color(0xFFF2EEFF),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 6),
              Text(value, style: Theme.of(context).textTheme.headlineSmall),
            ],
          ),
        ),
      ),
    );
  }
}

class QuestionsTab extends StatefulWidget {
  const QuestionsTab({super.key, required this.api});
  final ApiClient api;

  @override
  State<QuestionsTab> createState() => _QuestionsTabState();
}

class _QuestionsTabState extends State<QuestionsTab> {
  bool loading = true;
  String? error;
  List<QuestionItem> questions = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final page = await widget.api.fetchQuestionsPage(page: 1, pageSize: 50);
      if (!mounted) return;
      setState(() => questions = page.items);
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _openCreateSheet() async {
    final stemController = TextEditingController();
    final categoryController = TextEditingController(text: '未分类');
    int difficulty = 3;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) => Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 16,
              bottom: MediaQuery.of(context).viewInsets.bottom + 16,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: stemController, decoration: const InputDecoration(labelText: '题目内容')),
                const SizedBox(height: 10),
                TextField(controller: categoryController, decoration: const InputDecoration(labelText: '分类')),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  value: difficulty,
                  decoration: const InputDecoration(labelText: '难度'),
                  items: [1, 2, 3, 4, 5]
                      .map((v) => DropdownMenuItem(value: v, child: Text('难度 $v')))
                      .toList(),
                  onChanged: (v) => setSheetState(() => difficulty = v ?? 3),
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: () async {
                    if (stemController.text.trim().length < 3) return;
                    await widget.api.createQuestion(
                      stem: stemController.text.trim(),
                      category: categoryController.text.trim().isEmpty ? '未分类' : categoryController.text.trim(),
                      difficulty: difficulty,
                    );
                    if (!context.mounted) return;
                    Navigator.of(context).pop();
                    _load();
                  },
                  icon: const Icon(Icons.save_outlined),
                  label: const Text('创建题目'),
                ),
              ],
            ),
          ),
        );
      },
    );
    stemController.dispose();
    categoryController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('题库')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreateSheet,
        icon: const Icon(Icons.add),
        label: const Text('新增'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: loading
            ? const Center(child: CircularProgressIndicator())
            : error != null
                ? ListView(children: [Padding(padding: const EdgeInsets.all(16), child: Text(error!))])
                : ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: questions.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final q = questions[index];
                      return Card(
                        child: ListTile(
                          title: Text(q.stem),
                          subtitle: Text('${q.category} · 难度 ${q.difficulty} · 掌握度 ${q.masteryScore}'),
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}

class PracticeTab extends StatefulWidget {
  const PracticeTab({super.key, required this.api});
  final ApiClient api;

  @override
  State<PracticeTab> createState() => _PracticeTabState();
}

class _PracticeTabState extends State<PracticeTab> {
  final answerController = TextEditingController();
  bool loading = false;
  String? error;
  List<PracticeCategory> categories = [];
  String? selectedCategory;
  int selectedCount = 5;
  PracticeSession? session;
  int currentIndex = 0;
  String? latestAnalysis;
  String? latestReference;

  @override
  void initState() {
    super.initState();
    _loadCategories();
  }

  @override
  void dispose() {
    answerController.dispose();
    super.dispose();
  }

  Future<void> _loadCategories() async {
    setState(() => loading = true);
    try {
      final data = await widget.api.fetchPracticeCategories();
      if (!mounted) return;
      setState(() => categories = data);
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _startSession() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final data = await widget.api.startPracticeSession(selectedCategory, selectedCount);
      if (!mounted) return;
      setState(() {
        session = data;
        currentIndex = 0;
        latestAnalysis = null;
        latestReference = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _submitCurrent({required bool skip}) async {
    final current = session?.questions[currentIndex];
    if (current == null) return;
    if (!skip && answerController.text.trim().isEmpty) return;
    setState(() => loading = true);
    try {
      final result = skip
          ? await widget.api.skipPracticeAnswer(session!.sessionId, current.id)
          : await widget.api.submitPracticeAnswer(
              session!.sessionId,
              current.id,
              answerController.text.trim(),
            );
      if (!mounted) return;
      setState(() {
        latestAnalysis = result.analysis;
        latestReference = result.referenceAnswer;
        answerController.clear();
        if (currentIndex + 1 < session!.questions.length) {
          currentIndex += 1;
        }
      });
      final done = currentIndex + 1 >= session!.questions.length;
      if (done) {
        final summary = await widget.api.fetchPracticeSummary(session!.sessionId);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('本轮完成，总分 ${summary.totalScore}')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final current = session == null ? null : session!.questions[currentIndex];
    final sessionActive = session != null;
    return Scaffold(
      appBar: AppBar(title: const Text('练习')),
      body: RefreshIndicator(
        onRefresh: _loadCategories,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (error != null) Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            if (!sessionActive) ...[
              const Text('选择练习参数', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: categories
                    .where((c) => c.selectable)
                    .map(
                      (c) => ChoiceChip(
                        label: Text('${c.category} (${c.totalQuestions})'),
                        selected: selectedCategory == c.category,
                        backgroundColor: Colors.white,
                        selectedColor: const Color(0xFFE3DAFF),
                        onSelected: (_) => setState(() {
                          selectedCategory = selectedCategory == c.category ? null : c.category;
                        }),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 12),
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 5, label: Text('5 题')),
                  ButtonSegment(value: 10, label: Text('10 题')),
                  ButtonSegment(value: 15, label: Text('15 题')),
                ],
                selected: {selectedCount},
                onSelectionChanged: (v) => setState(() => selectedCount = v.first),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: loading ? null : _startSession,
                icon: const Icon(Icons.play_arrow),
                label: const Text('开始练习'),
              ),
            ] else ...[
              Text('第 ${currentIndex + 1}/${session!.questions.length} 题', style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(current!.stem),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: answerController,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: '你的答案',
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: loading ? null : () => _submitCurrent(skip: false),
                      child: const Text('提交'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: loading ? null : () => _submitCurrent(skip: true),
                      child: const Text('跳过'),
                    ),
                  ),
                ],
              ),
            ],
            if (latestAnalysis != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('AI 评语', style: TextStyle(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      Text(latestAnalysis!),
                      const SizedBox(height: 12),
                      const Text('参考答案', style: TextStyle(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      Text(latestReference ?? ''),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class ApiClient {
  ApiClient({required this.baseUrl});
  final String baseUrl;

  Uri _uri(String path, [Map<String, dynamic>? query]) =>
      Uri.parse('$baseUrl$path').replace(queryParameters: query?.map((k, v) => MapEntry(k, '$v')));

  Future<http.Response> _guardedRequest(
    Future<http.Response> Function() request, {
    required Uri uri,
    required String method,
  }) async {
    try {
      return await request();
    } catch (e, st) {
      throw ApiException(
        message: '网络请求异常($method)',
        url: uri.toString(),
        cause: e,
        stackTrace: st,
      );
    }
  }

  Future<List<QuestionItem>> fetchQuestions() async {
    final uri = _uri('/api/questions');
    final res = await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final jsonList = jsonDecode(utf8.decode(res.bodyBytes)) as List<dynamic>;
    return jsonList.map((e) => QuestionItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<QuestionPage> fetchQuestionsPage({required int page, required int pageSize}) async {
    final uri = _uri('/api/questions/page', {
      'page': page,
      'page_size': pageSize,
      'sort_by': 'created_at',
      'sort_order': 'desc',
    });
    final res = await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return QuestionPage.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<QuestionItem> createQuestion({
    required String stem,
    required String category,
    required int difficulty,
  }) async {
    final uri = _uri('/api/questions');
    final res = await _guardedRequest(
      () => http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'stem': stem, 'category': category, 'difficulty': difficulty}),
    ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return QuestionItem.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<List<PracticeCategory>> fetchPracticeCategories() async {
    final uri = _uri('/api/practice/categories');
    final res = await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final map = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return (map['categories'] as List<dynamic>)
        .map((e) => PracticeCategory.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PracticeSession> startPracticeSession(String? category, int count) async {
    final query = {'count': count, if (category != null) 'category': category};
    final uri = _uri('/api/practice/sessions/start', query);
    final res = await _guardedRequest(() => http.post(uri), uri: uri, method: 'POST');
    _check(res);
    return PracticeSession.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSubmitResult> submitPracticeAnswer(int sessionId, int questionId, String userAnswer) async {
    final uri = _uri('/api/practice/sessions/$sessionId/submit');
    final res = await _guardedRequest(
      () => http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'question_id': questionId, 'user_answer': userAnswer}),
    ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return PracticeSubmitResult.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSubmitResult> skipPracticeAnswer(int sessionId, int questionId) async {
    final uri = _uri('/api/practice/sessions/$sessionId/skip');
    final res = await _guardedRequest(
      () => http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'question_id': questionId}),
    ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return PracticeSubmitResult.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSummary> fetchPracticeSummary(int sessionId) async {
    final uri = _uri('/api/practice/sessions/$sessionId/summary');
    final res = await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return PracticeSummary.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  void _check(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) return;
    throw ApiException(
      message: '请求失败',
      url: res.request?.url.toString(),
      statusCode: res.statusCode,
      responseBody: utf8.decode(res.bodyBytes),
    );
  }
}

class ApiException implements Exception {
  ApiException({
    required this.message,
    this.url,
    this.statusCode,
    this.responseBody,
    this.cause,
    this.stackTrace,
  });

  final String message;
  final String? url;
  final int? statusCode;
  final String? responseBody;
  final Object? cause;
  final StackTrace? stackTrace;

  @override
  String toString() {
    final buf = StringBuffer()..writeln('ApiException: $message');
    if (url != null) buf.writeln('url: $url');
    if (statusCode != null) buf.writeln('statusCode: $statusCode');
    if (responseBody != null && responseBody!.isNotEmpty) {
      buf.writeln('responseBody: ${_shorten(responseBody!, 800)}');
    }
    if (cause != null) buf.writeln('cause: $cause');
    if (stackTrace != null) buf.writeln('stack: ${_shorten(stackTrace.toString(), 1200)}');
    return buf.toString().trim();
  }
}

String _formatError(Object e) {
  if (e is ApiException) return e.toString();
  return 'ExceptionType: ${e.runtimeType}\n$e';
}

String _shorten(String value, int maxLen) {
  final text = value.trim();
  if (text.length <= maxLen) return text;
  return '${text.substring(0, maxLen)}...(truncated)';
}

class QuestionItem {
  QuestionItem({
    required this.id,
    required this.stem,
    required this.category,
    required this.difficulty,
    required this.masteryScore,
  });

  final int id;
  final String stem;
  final String category;
  final int difficulty;
  final int masteryScore;

  factory QuestionItem.fromJson(Map<String, dynamic> json) => QuestionItem(
        id: json['id'] as int,
        stem: json['stem'] as String,
        category: json['category'] as String,
        difficulty: json['difficulty'] as int,
        masteryScore: json['mastery_score'] as int? ?? 0,
      );
}

class QuestionPage {
  QuestionPage({required this.total, required this.items});
  final int total;
  final List<QuestionItem> items;

  factory QuestionPage.fromJson(Map<String, dynamic> json) => QuestionPage(
        total: json['total'] as int? ?? 0,
        items: (json['items'] as List<dynamic>? ?? const [])
            .map((e) => QuestionItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PracticeCategory {
  PracticeCategory({required this.category, required this.totalQuestions, required this.selectable});
  final String category;
  final int totalQuestions;
  final bool selectable;

  factory PracticeCategory.fromJson(Map<String, dynamic> json) => PracticeCategory(
        category: json['category'] as String,
        totalQuestions: json['total_questions'] as int,
        selectable: json['selectable'] as bool,
      );
}

class PracticeSession {
  PracticeSession({required this.sessionId, required this.questions});
  final int sessionId;
  final List<QuestionItem> questions;

  factory PracticeSession.fromJson(Map<String, dynamic> json) => PracticeSession(
        sessionId: json['session_id'] as int,
        questions: (json['questions'] as List<dynamic>)
            .map((e) => QuestionItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PracticeSubmitResult {
  PracticeSubmitResult({required this.analysis, required this.referenceAnswer});
  final String analysis;
  final String referenceAnswer;

  factory PracticeSubmitResult.fromJson(Map<String, dynamic> json) => PracticeSubmitResult(
        analysis: json['analysis'] as String,
        referenceAnswer: json['reference_answer'] as String? ?? '',
      );
}

class PracticeSummary {
  PracticeSummary({required this.totalScore});
  final int totalScore;

  factory PracticeSummary.fromJson(Map<String, dynamic> json) => PracticeSummary(
        totalScore: json['total_score'] as int,
      );
}
