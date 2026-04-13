import 'dart:convert';

import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
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
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.all(Radius.circular(28))),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
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
      PracticeHistoryTab(api: _api),
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
              NavigationDestination(
                  icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home),
                  label: '首页'),
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
              NavigationDestination(
                icon: Icon(Icons.history_outlined),
                selectedIcon: Icon(Icons.history),
                label: '刷题记录',
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
  List<PracticeActivityDay> activityDays = [];
  String activityToday = '';
  List<PracticeSessionListItem> sessions = [];
  QuestionItem? dailyQuestion;
  int dailyQuestionRank = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    super.dispose();
  }

  int _fnv1a(String input) {
    var h = 2166136261;
    for (final c in input.codeUnits) {
      h ^= c;
      h = (h * 16777619) & 0xffffffff;
    }
    return h & 0x7fffffff;
  }

  String _todayKey() {
    final d = DateTime.now();
    final m = d.month.toString().padLeft(2, '0');
    final day = d.day.toString().padLeft(2, '0');
    return '${d.year}-$m-$day';
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final futures = await Future.wait([
        widget.api.fetchQuestions(sortBy: 'id', sortOrder: 'asc'),
        widget.api.fetchPracticeActivity(),
        widget.api.fetchPracticeSessions(),
      ]);
      final allQuestions = futures[0] as List<QuestionItem>;
      final activity = futures[1] as PracticeActivityResponse;
      final sessionList = futures[2] as List<PracticeSessionListItem>;
      final today = _todayKey();
      QuestionItem? picked;
      var pickedRank = 0;
      if (allQuestions.isNotEmpty) {
        pickedRank = _fnv1a('$today|daily-v1') % allQuestions.length;
        picked = allQuestions[pickedRank];
      }
      if (!mounted) return;
      setState(() {
        activityDays = activity.days;
        activityToday = activity.today;
        sessions = sessionList;
        dailyQuestion = picked;
        dailyQuestionRank = pickedRank;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Color _heatColor(int level) {
    if (level <= 0) return const Color(0xFFEBEDF0);
    if (level == 1) return const Color(0xFF9BE9A8);
    if (level == 2) return const Color(0xFF40C463);
    if (level == 3) return const Color(0xFF30A14E);
    return const Color(0xFF216E39);
  }

  List<List<PracticeActivityDay>> _weekColumns(int maxColumns) {
    final cols = <List<PracticeActivityDay>>[];
    for (var i = 0; i < activityDays.length; i += 7) {
      cols.add(activityDays.skip(i).take(7).toList());
    }
    if (cols.length <= maxColumns) return cols;
    return cols.sublist(cols.length - maxColumns);
  }

  List<({int index, String label})> _monthLabels(List<List<PracticeActivityDay>> cols) {
    var prev = '';
    final result = <({int index, String label})>[];
    for (var i = 0; i < cols.length; i++) {
      final col = cols[i];
      final date = col.isEmpty ? '' : col.first.date;
      if (date.length < 7) continue;
      final key = date.substring(0, 7);
      if (key == prev) continue;
      prev = key;
      final month = int.tryParse(date.substring(5, 7)) ?? 1;
      const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      result.add((index: i, label: names[(month - 1).clamp(0, 11)]));
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text(
              'INTERVIEW COLLECTOR',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 16),
            if (loading)
              const AppLoadingView(padding: EdgeInsets.all(24))
            else if (error != null)
              AppErrorText(error!)
            else
              const SizedBox.shrink(),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('做题热力图',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    LayoutBuilder(
                      builder: (context, constraints) {
                        const labelWidth = 30.0;
                        const cell = 10.0;
                        const gap = 3.0;
                        final available = (constraints.maxWidth - labelWidth).clamp(80.0, 1200.0);
                        const colWidth = cell + gap;
                        final maxCols = (available / colWidth).floor().clamp(1, 53);
                        final cols = _weekColumns(maxCols);
                        final months = _monthLabels(cols);
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const SizedBox(width: labelWidth),
                                SizedBox(
                                  width: cols.length * colWidth,
                                  height: 12,
                                  child: Stack(
                                    clipBehavior: Clip.none,
                                    children: months
                                        .map(
                                          (m) => Positioned(
                                            left: m.index * colWidth,
                                            child: Text(
                                              m.label,
                                              style: const TextStyle(fontSize: 9, color: Color(0xFF57606A)),
                                            ),
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(
                                  width: labelWidth,
                                  child: Column(
                                    children: [
                                      SizedBox(height: 10),
                                      SizedBox(height: 13, child: Align(alignment: Alignment.centerRight, child: Text('Mon', style: TextStyle(fontSize: 9, color: Color(0xFF57606A))))),
                                      SizedBox(height: 13),
                                      SizedBox(height: 13, child: Align(alignment: Alignment.centerRight, child: Text('Wed', style: TextStyle(fontSize: 9, color: Color(0xFF57606A))))),
                                      SizedBox(height: 13),
                                      SizedBox(height: 13, child: Align(alignment: Alignment.centerRight, child: Text('Fri', style: TextStyle(fontSize: 9, color: Color(0xFF57606A))))),
                                      SizedBox(height: 13),
                                    ],
                                  ),
                                ),
                                ...cols.map(
                                  (col) => SizedBox(
                                    width: colWidth,
                                    child: Column(
                                      children: col
                                          .map(
                                            (cellDay) => Container(
                                              width: cell,
                                              height: cell,
                                              margin: const EdgeInsets.only(bottom: gap),
                                              decoration: BoxDecoration(
                                                color: cellDay.date.compareTo(activityToday) > 0
                                                    ? const Color(0xFFEBEDF0)
                                                    : _heatColor(cellDay.level),
                                                borderRadius: BorderRadius.circular(2),
                                              ),
                                            ),
                                          )
                                          .toList(),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        );
                      },
                    ),
                    const SizedBox(height: 8),
                    const Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text('Less', style: TextStyle(fontSize: 10, color: Color(0xFF57606A))),
                        SizedBox(width: 4),
                        _LegendSwatch(Color(0xFFEBEDF0)),
                        _LegendSwatch(Color(0xFF9BE9A8)),
                        _LegendSwatch(Color(0xFF40C463)),
                        _LegendSwatch(Color(0xFF30A14E)),
                        _LegendSwatch(Color(0xFF216E39)),
                        SizedBox(width: 4),
                        Text('More', style: TextStyle(fontSize: 10, color: Color(0xFF57606A))),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('刷题得分率趋势',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    if (sessions.isEmpty)
                      const Text('暂无已完成刷题记录')
                    else
                      SizedBox(
                        height: 220,
                        child: LineChart(
                          LineChartData(
                            minY: 0,
                            maxY: 100,
                            titlesData: const FlTitlesData(
                              topTitles: AxisTitles(
                                  sideTitles: SideTitles(showTitles: false)),
                              rightTitles: AxisTitles(
                                  sideTitles: SideTitles(showTitles: false)),
                            ),
                            lineBarsData: [
                              LineChartBarData(
                                spots: List.generate(sessions.length, (i) {
                                  final s = sessions[i];
                                  final max = (s.questionCount) * 10;
                                  final pct = max <= 0
                                      ? 0.0
                                      : (s.totalScore * 100.0 / max);
                                  return FlSpot(i.toDouble(), pct);
                                }),
                                isCurved: true,
                                color: const Color(0xFF6D4DFF),
                                dotData: const FlDotData(show: true),
                                belowBarData: BarAreaData(
                                    show: true, color: const Color(0x336D4DFF)),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('每日一题',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    if (dailyQuestion == null)
                      const Text('暂无题目，请先导入或新增题目。')
                    else ...[
                      InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => DailyQuestionPage(
                              api: widget.api,
                              question: dailyQuestion!,
                              rank: dailyQuestionRank + 1,
                            ),
                          ),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('题面：${dailyQuestion!.stem}'),
                              const SizedBox(height: 6),
                              Text('分类：${dailyQuestion!.category}'),
                              Text('难度：${dailyQuestion!.difficulty}'),
                              Text('掌握度：${dailyQuestion!.masteryScore}%'),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class DailyQuestionPage extends StatefulWidget {
  const DailyQuestionPage({
    super.key,
    required this.api,
    required this.question,
    required this.rank,
  });

  final ApiClient api;
  final QuestionItem question;
  final int rank;

  @override
  State<DailyQuestionPage> createState() => _DailyQuestionPageState();
}

class _DailyQuestionPageState extends State<DailyQuestionPage> {
  final answerController = TextEditingController();
  bool submitting = false;
  PracticeSubmitResult? result;

  @override
  void dispose() {
    answerController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (answerController.text.trim().isEmpty) return;
    setState(() => submitting = true);
    try {
      final data = await widget.api.submitDailyPracticeAnswer(
        widget.question.id,
        answerController.text.trim(),
      );
      if (!mounted) return;
      setState(() => result = data);
    } finally {
      if (mounted) {
        setState(() => submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('每日一题作答')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('今日题目：第 ${widget.rank} 题'),
          const SizedBox(height: 8),
          Text('题面：${widget.question.stem}'),
          const SizedBox(height: 8),
          Text('分类：${widget.question.category}'),
          Text('难度：${widget.question.difficulty}'),
          Text('掌握度：${widget.question.masteryScore}%'),
          const SizedBox(height: 12),
          TextField(
            controller: answerController,
            minLines: 5,
            maxLines: 8,
            decoration: const InputDecoration(labelText: '输入你的答案'),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: submitting ? null : _submit,
            child: Text(submitting ? '判题中...' : '提交并判题'),
          ),
          if (result != null) ...[
            const SizedBox(height: 12),
            Text('得分：${result!.score} / 10'),
            const SizedBox(height: 8),
            const Text('解析：'),
            AppMarkdown(result!.analysis),
            const SizedBox(height: 8),
            const Text('参考答案：'),
            AppMarkdown(result!.referenceAnswer),
          ],
        ],
      ),
    );
  }
}

class AppLoadingView extends StatelessWidget {
  const AppLoadingView({super.key, this.padding = const EdgeInsets.all(20)});
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: padding,
        child: const CircularProgressIndicator(),
      ),
    );
  }
}

class AppEmptyCard extends StatelessWidget {
  const AppEmptyCard(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Card(
        child: Padding(padding: const EdgeInsets.all(14), child: Text(text)));
  }
}

class AppErrorText extends StatelessWidget {
  const AppErrorText(this.error, {super.key});
  final String error;

  @override
  Widget build(BuildContext context) {
    return Text(error,
        style: TextStyle(color: Theme.of(context).colorScheme.error));
  }
}

class AppMarkdown extends StatelessWidget {
  const AppMarkdown(this.data, {super.key});
  final String data;

  @override
  Widget build(BuildContext context) {
    final text = data.trim().isEmpty ? '-' : data.trim();
    return MarkdownBody(
      data: text,
      selectable: true,
      styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
        p: Theme.of(context).textTheme.bodyMedium,
      ),
    );
  }
}

class _LegendSwatch extends StatelessWidget {
  const _LegendSwatch(this.color);
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 10,
      height: 10,
      margin: const EdgeInsets.symmetric(horizontal: 1),
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2)),
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
  bool loadingMore = false;
  bool hasMore = true;
  String? error;
  List<QuestionItem> questions = [];
  List<String> categoryOptions = [];
  int total = 0;
  int page = 1;
  int pageSize = 20;
  String category = '';
  String categoryKeyword = '';
  int? difficulty;
  String sortMode = 'recent_desc';
  bool filterExpanded = false;
  final scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    scrollController.addListener(_onScroll);
    _loadBootstrap();
  }

  @override
  void dispose() {
    scrollController
      ..removeListener(_onScroll)
      ..dispose();
    super.dispose();
  }

  Future<void> _loadBootstrap() async {
    setState(() {
      error = null;
    });
    try {
      final cats = await widget.api.fetchCategoryNames();
      categoryOptions = cats;
      await _load(reset: true);
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  ({String sortBy, String sortOrder}) _sortParams() {
    switch (sortMode) {
      case 'created_asc':
        return (sortBy: 'created_at', sortOrder: 'asc');
      case 'mastery_desc':
        return (sortBy: 'mastery_score', sortOrder: 'desc');
      case 'mastery_asc':
        return (sortBy: 'mastery_score', sortOrder: 'asc');
      case 'recent_asc':
        return (sortBy: 'recent_encountered', sortOrder: 'asc');
      case 'recent_desc':
        return (sortBy: 'recent_encountered', sortOrder: 'desc');
      default:
        return (sortBy: 'created_at', sortOrder: 'desc');
    }
  }

  Future<void> _load({bool reset = false}) async {
    if (loadingMore || (!reset && loading)) return;
    if (!reset && !hasMore) return;
    setState(() {
      if (reset) {
        loading = true;
      } else {
        loadingMore = true;
      }
      error = null;
    });
    try {
      final sort = _sortParams();
      final requestPage = reset ? 1 : page;
      final pageData = await widget.api.fetchQuestionsPage(
        page: requestPage,
        pageSize: pageSize,
        category: category.trim().isEmpty ? null : category.trim(),
        difficulty: difficulty,
        sortBy: sort.sortBy,
        sortOrder: sort.sortOrder,
      );
      if (!mounted) return;
      setState(() {
        if (reset) {
          questions = pageData.items;
        } else {
          questions = [...questions, ...pageData.items];
        }
        total = pageData.total;
        page = pageData.page + 1;
        pageSize = pageData.pageSize;
        hasMore = questions.length < total && pageData.items.isNotEmpty;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) {
        setState(() {
          loading = false;
          loadingMore = false;
        });
      }
    }
  }

  void _onScroll() {
    if (!scrollController.hasClients || loading || loadingMore || !hasMore) {
      return;
    }
    if (scrollController.position.extentAfter < 300) {
      _load();
    }
  }

  Future<void> _reloadWithFilters() async {
    page = 1;
    hasMore = true;
    await _load(reset: true);
  }

  List<String> get filteredCategoryOptions {
    final key = categoryKeyword.trim();
    if (key.isEmpty) return categoryOptions;
    return categoryOptions
        .where((c) => c.toLowerCase().contains(key.toLowerCase()))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('题库')),
      body: RefreshIndicator(
        onRefresh: () => _load(reset: true),
        child: ListView(
          controller: scrollController,
          padding: const EdgeInsets.all(12),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    InkWell(
                      onTap: () => setState(() => filterExpanded = !filterExpanded),
                      child: Row(
                        children: [
                          const Text('筛选', style: TextStyle(fontWeight: FontWeight.w700)),
                          const Spacer(),
                          Icon(filterExpanded ? Icons.expand_less : Icons.expand_more),
                        ],
                      ),
                    ),
                    if (filterExpanded) ...[
                      const SizedBox(height: 8),
                      TextField(
                        decoration: const InputDecoration(labelText: '分类查找（关键词）'),
                        onChanged: (v) => setState(() => categoryKeyword = v),
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        value: category.isEmpty ? '' : category,
                        items: [
                          const DropdownMenuItem(value: '', child: Text('全部分类')),
                          ...filteredCategoryOptions.map((c) => DropdownMenuItem(value: c, child: Text(c))),
                        ],
                        onChanged: (v) {
                          setState(() => category = v ?? '');
                          _reloadWithFilters();
                        },
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<int?>(
                        value: difficulty,
                        items: const [
                          DropdownMenuItem<int?>(value: null, child: Text('全部难度')),
                          DropdownMenuItem<int?>(value: 1, child: Text('难度 1')),
                          DropdownMenuItem<int?>(value: 2, child: Text('难度 2')),
                          DropdownMenuItem<int?>(value: 3, child: Text('难度 3')),
                          DropdownMenuItem<int?>(value: 4, child: Text('难度 4')),
                          DropdownMenuItem<int?>(value: 5, child: Text('难度 5')),
                        ],
                        onChanged: (v) {
                          setState(() => difficulty = v);
                          _reloadWithFilters();
                        },
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        value: sortMode,
                        items: const [
                          DropdownMenuItem(value: 'recent_desc', child: Text('最近遇到：近到远（默认）')),
                          DropdownMenuItem(value: 'recent_asc', child: Text('最近遇到：远到近')),
                          DropdownMenuItem(value: 'created_desc', child: Text('入库时间：新到旧')),
                          DropdownMenuItem(value: 'created_asc', child: Text('入库时间：旧到新')),
                          DropdownMenuItem(value: 'mastery_desc', child: Text('掌握度：高到低')),
                          DropdownMenuItem(value: 'mastery_asc', child: Text('掌握度：低到高')),
                        ],
                        onChanged: (v) {
                          setState(() => sortMode = v ?? 'recent_desc');
                          _reloadWithFilters();
                        },
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
            if (loading)
              const AppLoadingView()
            else if (error != null)
              Padding(
                padding: const EdgeInsets.all(8),
                child: AppErrorText(error!),
              )
            else ...[
              ...questions.map(
                (q) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Card(
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () async {
                        final changed = await Navigator.of(context).push<bool>(
                          MaterialPageRoute(
                            builder: (_) => QuestionDetailPage(
                              api: widget.api,
                              question: q,
                              categoryOptions: categoryOptions,
                            ),
                          ),
                        );
                        if (changed == true) {
                          await _load(reset: true);
                        }
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(q.stem),
                            const SizedBox(height: 6),
                            Text('分类：${q.category} ｜ 难度：${q.difficultyStars}'),
                            const SizedBox(height: 6),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: LinearProgressIndicator(
                                value: (q.masteryScore.clamp(0, 100)) / 100,
                                minHeight: 10,
                                backgroundColor: const Color(0xFFEFEFFF),
                                valueColor: const AlwaysStoppedAnimation(Color(0xFF6D4DFF)),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text('完成度：${q.masteryScore}%'),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              if (loadingMore)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(child: CircularProgressIndicator()),
                ),
              if (!hasMore)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(child: Text('已加载全部题目')),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class QuestionDetailPage extends StatefulWidget {
  const QuestionDetailPage({
    super.key,
    required this.api,
    required this.question,
    required this.categoryOptions,
  });
  final ApiClient api;
  final QuestionItem question;
  final List<String> categoryOptions;

  @override
  State<QuestionDetailPage> createState() => _QuestionDetailPageState();
}

class _QuestionDetailPageState extends State<QuestionDetailPage> {
  late QuestionItem question;
  List<PracticeRecordItem> records = [];
  bool recordsLoading = true;
  bool editMode = false;
  bool refreshingReference = false;
  bool singleSubmitting = false;
  String? singleResult;
  final singleAnswerController = TextEditingController();
  final editStemController = TextEditingController();
  final editCategoryController = TextEditingController();
  int editDifficulty = 3;
  bool changed = false;

  @override
  void initState() {
    super.initState();
    question = widget.question;
    editStemController.text = question.stem;
    editCategoryController.text = question.category;
    editDifficulty = question.difficulty;
    _loadRecords();
  }

  @override
  void dispose() {
    singleAnswerController.dispose();
    editStemController.dispose();
    editCategoryController.dispose();
    super.dispose();
  }

  Future<void> _loadRecords() async {
    setState(() => recordsLoading = true);
    try {
      records = await widget.api.fetchQuestionRecords(question.id);
    } finally {
      if (mounted) setState(() => recordsLoading = false);
    }
  }

  List<FlSpot> _buildSpots() {
    final sorted = [...records]
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return List.generate(sorted.length,
        (i) => FlSpot(i.toDouble(), sorted[i].aiScore.toDouble()));
  }

  @override
  Widget build(BuildContext context) {
    final spots = _buildSpots();
    return Scaffold(
      appBar: AppBar(title: const Text('题目详情与操作')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(question.stem, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
              '分类：${question.category} ｜ 难度：${question.difficulty} ｜ 掌握度：${question.masteryScore}%'),
          const SizedBox(height: 10),
          const Text('参考答案：'),
          AppMarkdown(question.referenceAnswer.isEmpty ? '暂无' : question.referenceAnswer),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: () => setState(() => editMode = !editMode),
                child: Text(editMode ? '取消编辑' : '编辑题目'),
              ),
              OutlinedButton(
                onPressed: () async {
                  final ok = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('确认删除'),
                      content: const Text('确认删除这道题吗？'),
                      actions: [
                        TextButton(
                            onPressed: () => Navigator.pop(ctx, false),
                            child: const Text('取消')),
                        FilledButton(
                            onPressed: () => Navigator.pop(ctx, true),
                            child: const Text('删除')),
                      ],
                    ),
                  );
                  if (ok != true) return;
                  await widget.api.deleteQuestion(question.id);
                  if (!context.mounted) return;
                  Navigator.of(context).pop(true);
                },
                child: const Text('删除题目'),
              ),
              OutlinedButton(
                onPressed: refreshingReference
                    ? null
                    : () async {
                        setState(() => refreshingReference = true);
                        try {
                          question = await widget.api
                              .refreshQuestionReference(question.id);
                          changed = true;
                          editStemController.text = question.stem;
                          editCategoryController.text = question.category;
                          editDifficulty = question.difficulty;
                        } finally {
                          if (mounted) {
                            setState(() => refreshingReference = false);
                          }
                        }
                      },
                child: Text(refreshingReference ? '刷新中...' : '仅刷新参考答案'),
              ),
              OutlinedButton(
                  onPressed: _loadRecords, child: const Text('刷新做题记录')),
            ],
          ),
          if (editMode) ...[
            const SizedBox(height: 12),
            TextField(
                controller: editStemController,
                minLines: 2,
                maxLines: 4,
                decoration: const InputDecoration(labelText: '题干')),
            const SizedBox(height: 8),
            TextField(
                controller: editCategoryController,
                decoration: const InputDecoration(labelText: '分类')),
            const SizedBox(height: 8),
            DropdownButtonFormField<int>(
              value: editDifficulty,
              decoration: const InputDecoration(labelText: '难度'),
              items: [1, 2, 3, 4, 5]
                  .map((v) => DropdownMenuItem(value: v, child: Text('难度 $v')))
                  .toList(),
              onChanged: (v) => setState(() => editDifficulty = v ?? 3),
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: () async {
                if (editStemController.text.trim().length < 3) return;
                question = await widget.api.updateQuestion(
                  question.id,
                  stem: editStemController.text.trim(),
                  category: editCategoryController.text.trim().isEmpty
                      ? '未分类'
                      : editCategoryController.text.trim(),
                  difficulty: editDifficulty,
                );
                changed = true;
                if (!mounted) return;
                setState(() => editMode = false);
              },
              child: const Text('保存编辑'),
            ),
          ],
          const SizedBox(height: 12),
          TextField(
            controller: singleAnswerController,
            minLines: 3,
            maxLines: 5,
            decoration: const InputDecoration(labelText: '单题独立判题 - 你的答案'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: singleSubmitting
                ? null
                : () async {
                    if (singleAnswerController.text.trim().isEmpty) return;
                    setState(() => singleSubmitting = true);
                    try {
                      final data = await widget.api.submitDailyPracticeAnswer(
                        question.id,
                        singleAnswerController.text.trim(),
                      );
                      singleResult =
                          '得分：${data.score}/10\n\n解析：\n${data.analysis}\n\n参考答案：\n${data.referenceAnswer}';
                      await _loadRecords();
                      changed = true;
                    } finally {
                      if (mounted) setState(() => singleSubmitting = false);
                    }
                  },
            child: Text(singleSubmitting ? '判题中...' : '提交并判题'),
          ),
          if (singleResult != null) ...[
            const SizedBox(height: 8),
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(singleResult!))),
          ],
          const SizedBox(height: 14),
          Text('历次得分趋势', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (spots.length < 2)
            const Text('做题记录不足，暂无趋势图')
          else
            SizedBox(
              height: 220,
              child: LineChart(
                LineChartData(
                  minY: 0,
                  maxY: 10,
                  gridData: const FlGridData(show: true),
                  titlesData: const FlTitlesData(
                    topTitles:
                        AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles:
                        AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      dotData: const FlDotData(show: true),
                      color: const Color(0xFF6D4DFF),
                      belowBarData: BarAreaData(
                        show: true,
                        color: const Color(0x336D4DFF),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 14),
          Text('做题记录', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (recordsLoading)
            const Center(
                child: Padding(
                    padding: EdgeInsets.all(12),
                    child: CircularProgressIndicator()))
          else if (records.isEmpty)
            const Text('暂无做题记录')
          else
            ...records.map(
              (r) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('评分：${r.aiScore}/10'),
                      const SizedBox(height: 4),
                      Text('用户答案：${r.userAnswer.isEmpty ? "-" : r.userAnswer}'),
                      const SizedBox(height: 4),
                      const Text('AI 解析：'),
                      AppMarkdown(r.aiAnswer),
                      const SizedBox(height: 4),
                      Text('时间：${r.createdAt}'),
                    ],
                  ),
                ),
              ),
            ),
          const SizedBox(height: 18),
          OutlinedButton(
            onPressed: () => Navigator.pop(context, changed),
            child: const Text('返回题库'),
          ),
        ],
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

enum TrainMode { practice, memorize }

class _PracticeTabState extends State<PracticeTab> {
  static const List<int> sessionSizes = [5, 10, 15];

  final answerController = TextEditingController();
  bool loading = false;
  String? error;
  TrainMode mode = TrainMode.practice;

  List<PracticeCategory> categories = [];
  int totalQuestionsAll = 0;
  String selectedCategory = '';
  int selectedCount = 10;

  PracticeSession? session;
  int currentIndex = 0;
  PracticeSummary? summary;
  final Map<int, PracticeSubmitResult> perQuestionResult = {};

  List<QuestionItem> memorizeQuestions = [];
  int memorizeIndex = 0;
  bool memorizePrepared = false;
  bool filterExpanded = false;

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
      setState(() {
        categories = data;
        totalQuestionsAll =
            data.fold(0, (sum, item) => sum + item.totalQuestions);
        if (selectedCategory.isEmpty) {
          final firstOk =
              data.where((e) => e.totalQuestions >= selectedCount).toList();
          selectedCategory = firstOk.isNotEmpty ? firstOk.first.category : '';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  bool get canStartPractice {
    if (selectedCategory.isEmpty) return totalQuestionsAll >= selectedCount;
    final hit =
        categories.where((c) => c.category == selectedCategory).toList();
    return hit.isNotEmpty && hit.first.totalQuestions >= selectedCount;
  }

  bool get canStartMemorize {
    if (selectedCategory.isEmpty) return false;
    final hit =
        categories.where((c) => c.category == selectedCategory).toList();
    return hit.isNotEmpty && hit.first.totalQuestions >= selectedCount;
  }

  QuestionItem? get currentQuestion =>
      session == null || currentIndex >= session!.questions.length
          ? null
          : session!.questions[currentIndex];

  QuestionItem? get currentMemorizeQuestion =>
      memorizeIndex >= memorizeQuestions.length
          ? null
          : memorizeQuestions[memorizeIndex];

  bool get finished =>
      session != null &&
      currentIndex >= session!.questions.length &&
      session!.questions.isNotEmpty;

  void _clearPracticeState() {
    session = null;
    currentIndex = 0;
    summary = null;
    answerController.clear();
    perQuestionResult.clear();
  }

  Future<void> _startSession() async {
    if (!canStartPractice) {
      setState(() {
        error = selectedCategory.isNotEmpty
            ? '该分类题目不足 $selectedCount 道，请换分类或减小题量'
            : '全库题目不足 $selectedCount 道，请减小题量或先导入题目';
      });
      return;
    }
    setState(() {
      loading = true;
      error = null;
      _clearPracticeState();
    });
    try {
      final data = await widget.api.startPracticeSession(
        selectedCategory.isEmpty ? null : selectedCategory,
        selectedCount,
      );
      if (!mounted) return;
      setState(() => session = data);
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _prepareMemorize() async {
    if (!canStartMemorize) {
      setState(() => error = '背题模式需要选择具体分类，且题量不少于 $selectedCount');
      return;
    }
    setState(() {
      loading = true;
      error = null;
      _clearPracticeState();
      memorizePrepared = false;
      memorizeQuestions = [];
      memorizeIndex = 0;
    });
    try {
      final pool = await widget.api.fetchQuestions(category: selectedCategory);
      if (pool.length < selectedCount) {
        setState(() => error = '该分类不足 $selectedCount 题，无法进入背题模式');
        return;
      }
      pool.shuffle();
      if (!mounted) return;
      setState(() {
        memorizeQuestions = pool.take(selectedCount).toList();
        memorizePrepared = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _startQuizFromMemorize() async {
    if (memorizeQuestions.length != selectedCount) return;
    setState(() {
      loading = true;
      error = null;
      _clearPracticeState();
    });
    try {
      final ids = memorizeQuestions.map((e) => e.id).toList()..shuffle();
      final data = await widget.api.startPracticeSessionCustom(ids);
      if (!mounted) return;
      setState(() {
        mode = TrainMode.practice;
        session = data;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _submitCurrent() async {
    final current = currentQuestion;
    if (current == null) return;
    if (answerController.text.trim().isEmpty) {
      setState(() => error = '请先填写答案');
      return;
    }
    setState(() => loading = true);
    try {
      final result = await widget.api.submitPracticeAnswer(
        session!.sessionId,
        current.id,
        answerController.text.trim(),
      );
      if (!mounted) return;
      setState(() => perQuestionResult[current.id] = result);
    } catch (e) {
      if (!mounted) return;
      setState(() => error = _formatError(e));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _nextQuestion() async {
    final current = currentQuestion;
    if (current == null) return;
    if (!perQuestionResult.containsKey(current.id)) {
      setState(() => loading = true);
      try {
        final data =
            await widget.api.skipPracticeAnswer(session!.sessionId, current.id);
        perQuestionResult[current.id] = data;
      } catch (e) {
        if (!mounted) return;
        setState(() => error = _formatError(e));
        return;
      } finally {
        if (mounted) setState(() => loading = false);
      }
    }
    setState(() {
      currentIndex += 1;
      answerController.clear();
      error = null;
    });
    if (finished) {
      final s = await widget.api.fetchPracticeSummary(session!.sessionId);
      if (!mounted) return;
      setState(() => summary = s);
    }
  }

  Widget _buildStartButton() {
    final isPractice = mode == TrainMode.practice;
    final enabled = isPractice ? canStartPractice : canStartMemorize;
    final onPressed = isPractice ? _startSession : _prepareMemorize;
    return SizedBox(
      width: 180,
      height: 180,
      child: FilledButton(
        style: FilledButton.styleFrom(
          shape: const CircleBorder(),
          textStyle: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
        ),
        onPressed: enabled ? onPressed : null,
        child: const Text('START'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final current = currentQuestion;
    final currentResult =
        current == null ? null : perQuestionResult[current.id];
    final maxScore =
        (summary?.questionCount ?? session?.questions.length ?? 10) * 10;
    final shouldShowStartOnly = !loading && session == null && !memorizePrepared;
    return Scaffold(
      appBar: AppBar(title: const Text('练习')),
      body: RefreshIndicator(
        onRefresh: _loadCategories,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (error != null) AppErrorText(error!),
            if (shouldShowStartOnly)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InkWell(
                        onTap: () => setState(() => filterExpanded = !filterExpanded),
                        child: Row(
                          children: [
                            const Text('训练设置', style: TextStyle(fontWeight: FontWeight.w700)),
                            const Spacer(),
                            Icon(filterExpanded ? Icons.expand_less : Icons.expand_more),
                          ],
                        ),
                      ),
                      if (filterExpanded) ...[
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            FilledButton(
                              onPressed: mode == TrainMode.practice ? null : () => setState(() => mode = TrainMode.practice),
                              child: const Text('刷题模式'),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton(
                              onPressed: mode == TrainMode.memorize ? null : () => setState(() => mode = TrainMode.memorize),
                              child: const Text('背题模式'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          children: sessionSizes
                              .map(
                                (n) => ChoiceChip(
                                  label: Text('$n 题'),
                                  selected: selectedCount == n,
                                  onSelected: (_) => setState(() => selectedCount = n),
                                ),
                              )
                              .toList(),
                        ),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<String>(
                          value: selectedCategory,
                          items: [
                            if (mode == TrainMode.practice) const DropdownMenuItem(value: '', child: Text('全部分类随机')),
                            ...categories.map(
                              (item) => DropdownMenuItem(
                                value: item.category,
                                enabled: item.totalQuestions >= selectedCount,
                                child: Text(
                                  '${item.category}（${item.totalQuestions}题）${item.totalQuestions < selectedCount ? ' — 不足$selectedCount题' : ''}',
                                ),
                              ),
                            ),
                          ],
                          onChanged: (v) => setState(() => selectedCategory = v ?? ''),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            if (loading) const AppLoadingView(),
            if (shouldShowStartOnly)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 80),
                child: Center(
                  child: _buildStartButton(),
                ),
              ),
            if (mode == TrainMode.memorize &&
                memorizePrepared &&
                memorizeIndex < memorizeQuestions.length) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                          '背题进度：第 ${memorizeIndex + 1} / ${memorizeQuestions.length} 题'),
                      const SizedBox(height: 8),
                      Text(currentMemorizeQuestion?.stem ?? ''),
                      const SizedBox(height: 8),
                      Text(
                          '参考答案：\n${currentMemorizeQuestion?.referenceAnswer.isEmpty ?? true ? "暂无参考答案" : currentMemorizeQuestion!.referenceAnswer}'),
                      const SizedBox(height: 10),
                      FilledButton(
                        onPressed: () => setState(() => memorizeIndex += 1),
                        child: const Text('下一题'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (mode == TrainMode.memorize &&
                memorizePrepared &&
                memorizeIndex >= memorizeQuestions.length &&
                memorizeQuestions.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('背题完成'),
                      const SizedBox(height: 8),
                      Text('将进入刷题模式，对刚才这 ${memorizeQuestions.length} 题进行乱序测验。'),
                      const SizedBox(height: 8),
                      FilledButton(
                          onPressed: _startQuizFromMemorize,
                          child: const Text('开始测验')),
                    ],
                  ),
                ),
              ),
            ],
            if (current != null && !finished) ...[
              Text('第 ${currentIndex + 1}/${session!.questions.length} 题',
                  style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(current.stem),
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
                      onPressed: loading ? null : _submitCurrent,
                      child: Text(loading ? '判题中...' : '提交并判题'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: loading ? null : _nextQuestion,
                      child: const Text('下一题'),
                    ),
                  ),
                ],
              ),
              if (currentResult != null) ...[
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('得分：${currentResult.score} / 10'),
                        const SizedBox(height: 8),
                        const Text('解析：',
                            style: TextStyle(fontWeight: FontWeight.w600)),
                        AppMarkdown(currentResult.analysis),
                        const SizedBox(height: 8),
                        const Text('参考答案：',
                            style: TextStyle(fontWeight: FontWeight.w600)),
                        AppMarkdown(currentResult.referenceAnswer),
                      ],
                    ),
                  ),
                ),
              ],
            ],
            if (finished && summary != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('本轮完成',
                          style: TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Text('总分：${summary!.totalScore} / $maxScore'),
                      Text('记录ID：${summary!.recordIds.join(", ")}'),
                      Text('会话ID：${summary!.sessionId}'),
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

class PracticeHistoryTab extends StatefulWidget {
  const PracticeHistoryTab({super.key, required this.api});
  final ApiClient api;

  @override
  State<PracticeHistoryTab> createState() => _PracticeHistoryTabState();
}

class _PracticeHistoryTabState extends State<PracticeHistoryTab> {
  bool loading = true;
  String? error;
  List<PracticeSessionListItem> sessions = [];

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
      sessions = await widget.api.fetchPracticeSessions();
    } catch (e) {
      error = _formatError(e);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('刷题记录')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (error != null) AppErrorText(error!),
            if (loading)
              const AppLoadingView()
            else if (sessions.isEmpty)
              const AppEmptyCard('暂无已完成刷题记录')
            else
              ...sessions.map(
                (s) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Card(
                    child: ListTile(
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PracticeSessionDetailPage(api: widget.api, sessionId: s.id),
                        ),
                      ),
                      title: Text('总分：${s.totalScore}/${s.questionCount * 10}'),
                      subtitle: Text('时间：${s.completedAt ?? "-"}'),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class PracticeSessionDetailPage extends StatelessWidget {
  const PracticeSessionDetailPage({super.key, required this.api, required this.sessionId});
  final ApiClient api;
  final int sessionId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('刷题详情')),
      body: FutureBuilder<PracticeSessionRecordsResponse>(
        future: api.fetchPracticeSessionRecords(sessionId),
        builder: (context, snapshot) {
          if (!snapshot.hasData) return const AppLoadingView();
          final data = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('会话：#$sessionId'),
              Text('总分：${data.totalScore}/${data.questionCount * 10}'),
              Text('时间：${data.completedAt ?? "-"}'),
              const SizedBox(height: 10),
              ...data.records.map(
                (r) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('评分：${r.aiScore}/10'),
                        Text('用户答案：${r.userAnswer.isEmpty ? "-" : r.userAnswer}'),
                        const Text('AI 解析：'),
                        AppMarkdown(r.aiAnswer),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class AnswerRecordsTab extends StatefulWidget {
  const AnswerRecordsTab({super.key, required this.api});
  final ApiClient api;

  @override
  State<AnswerRecordsTab> createState() => _AnswerRecordsTabState();
}

class _AnswerRecordsTabState extends State<AnswerRecordsTab> {
  bool loading = true;
  String? error;
  int total = 0;
  int page = 1;
  int pageSize = 25;
  String shanghaiDate = '';
  int? expandedId;
  List<PracticeRecordFeedItem> items = [];
  final dateController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    dateController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final data = await widget.api.fetchPracticeRecordFeed(
        page: page,
        pageSize: pageSize,
        shanghaiDate: shanghaiDate.isEmpty ? null : shanghaiDate,
      );
      total = data.total;
      items = data.items;
    } catch (e) {
      error = _formatError(e);
      total = 0;
      items = [];
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final totalPages = (total / pageSize).ceil().clamp(1, 100000);
    return Scaffold(
      appBar: AppBar(title: const Text('答题记录')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Wrap(
                  runSpacing: 8,
                  spacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    SizedBox(
                      width: 220,
                      child: TextField(
                        controller: dateController,
                        decoration: const InputDecoration(
                            labelText: '按记录日期筛选（YYYY-MM-DD）'),
                      ),
                    ),
                    FilledButton(
                      onPressed: () {
                        page = 1;
                        shanghaiDate = dateController.text.trim();
                        _load();
                      },
                      child: const Text('应用'),
                    ),
                    OutlinedButton(
                      onPressed: () {
                        dateController.clear();
                        shanghaiDate = '';
                        page = 1;
                        _load();
                      },
                      child: const Text('清除日期'),
                    ),
                    Text('共 $total 条'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            if (error != null) AppErrorText(error!),
            if (loading)
              const AppLoadingView()
            else if (items.isEmpty)
              const AppEmptyCard('暂无记录')
            else ...[
              ...items.map(
                (r) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              '${r.createdAt} ｜ ${r.sessionId == null ? "每日一题 / 无会话" : "训练会话 #${r.sessionId}"}'),
                          const SizedBox(height: 4),
                          Text('题目：${r.questionStem}'),
                          Text('得分：${r.aiScore}/10'),
                          const SizedBox(height: 4),
                          TextButton(
                            onPressed: () => setState(() =>
                                expandedId = expandedId == r.id ? null : r.id),
                            child: Text(expandedId == r.id ? '收起' : '详情'),
                          ),
                          if (expandedId == r.id) ...[
                            Text(
                                '作答：${r.userAnswer.isEmpty ? "（空，可能为跳过）" : r.userAnswer}'),
                            const SizedBox(height: 4),
                            const Text('AI 解析：'),
                            AppMarkdown(r.aiAnswer),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Row(
                children: [
                  OutlinedButton(
                    onPressed: page <= 1
                        ? null
                        : () {
                            page -= 1;
                            _load();
                          },
                    child: const Text('上一页'),
                  ),
                  const SizedBox(width: 8),
                  Text('第 $page / $totalPages 页'),
                  const SizedBox(width: 8),
                  OutlinedButton(
                    onPressed: page >= totalPages
                        ? null
                        : () {
                            page += 1;
                            _load();
                          },
                    child: const Text('下一页'),
                  ),
                  const Spacer(),
                  DropdownButton<int>(
                    value: pageSize,
                    items: const [15, 25, 50]
                        .map((v) =>
                            DropdownMenuItem(value: v, child: Text('每页 $v')))
                        .toList(),
                    onChanged: (v) {
                      if (v == null) return;
                      pageSize = v;
                      page = 1;
                      _load();
                    },
                  ),
                ],
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
      Uri.parse('$baseUrl$path')
          .replace(queryParameters: query?.map((k, v) => MapEntry(k, '$v')));

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

  Future<List<QuestionItem>> fetchQuestions({
    String? category,
    String sortBy = 'created_at',
    String sortOrder = 'desc',
  }) async {
    final uri = _uri('/api/questions', {
      if (category != null && category.isNotEmpty) 'category': category,
      'sort_by': sortBy,
      'sort_order': sortOrder,
    });
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final jsonList = jsonDecode(utf8.decode(res.bodyBytes)) as List<dynamic>;
    return jsonList
        .map((e) => QuestionItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<QuestionPage> fetchQuestionsPage({
    required int page,
    required int pageSize,
    String? category,
    int? difficulty,
    String sortBy = 'created_at',
    String sortOrder = 'desc',
  }) async {
    final query = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      'sort_by': sortBy,
      'sort_order': sortOrder,
      if (category != null && category.isNotEmpty) 'category': category,
      if (difficulty != null) 'difficulty': difficulty,
    };
    final uri = _uri('/api/questions/page', query);
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return QuestionPage.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
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
        body: jsonEncode(
            {'stem': stem, 'category': category, 'difficulty': difficulty}),
      ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return QuestionItem.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<QuestionItem> updateQuestion(
    int id, {
    required String stem,
    required String category,
    required int difficulty,
  }) async {
    final uri = _uri('/api/questions/$id');
    final res = await _guardedRequest(
      () => http.put(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(
            {'stem': stem, 'category': category, 'difficulty': difficulty}),
      ),
      uri: uri,
      method: 'PUT',
    );
    _check(res);
    return QuestionItem.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<void> deleteQuestion(int id) async {
    final uri = _uri('/api/questions/$id');
    final res = await _guardedRequest(() => http.delete(uri),
        uri: uri, method: 'DELETE');
    _check(res);
  }

  Future<QuestionItem> refreshQuestionReference(int id) async {
    final uri = _uri('/api/questions/$id/refresh-reference');
    final res =
        await _guardedRequest(() => http.post(uri), uri: uri, method: 'POST');
    _check(res);
    return QuestionItem.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<List<PracticeRecordItem>> fetchQuestionRecords(int id) async {
    final uri = _uri('/api/questions/$id/records');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final list = jsonDecode(utf8.decode(res.bodyBytes)) as List<dynamic>;
    return list
        .map((e) => PracticeRecordItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PracticeSubmitResult> submitDailyPracticeAnswer(
      int questionId, String userAnswer) async {
    final uri = _uri('/api/practice/daily/submit');
    final res = await _guardedRequest(
      () => http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body:
            jsonEncode({'question_id': questionId, 'user_answer': userAnswer}),
      ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return PracticeSubmitResult.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<List<String>> fetchCategoryNames() async {
    final uri = _uri('/api/categories');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final list = jsonDecode(utf8.decode(res.bodyBytes)) as List<dynamic>;
    return list
        .map((e) => (e as Map<String, dynamic>)['name'] as String)
        .toList();
  }

  Future<List<PracticeCategory>> fetchPracticeCategories() async {
    final uri = _uri('/api/practice/categories');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final map = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return (map['categories'] as List<dynamic>)
        .map((e) => PracticeCategory.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PracticeActivityResponse> fetchPracticeActivity() async {
    final uri = _uri('/api/practice/activity');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return PracticeActivityResponse.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<List<PracticeSessionListItem>> fetchPracticeSessions() async {
    final uri = _uri('/api/practice/sessions');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    final list = jsonDecode(utf8.decode(res.bodyBytes)) as List<dynamic>;
    return list
        .map((e) => PracticeSessionListItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PracticeSessionRecordsResponse> fetchPracticeSessionRecords(
      int sessionId) async {
    final uri = _uri('/api/practice/sessions/$sessionId/records');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return PracticeSessionRecordsResponse.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeRecordFeedPage> fetchPracticeRecordFeed({
    required int page,
    required int pageSize,
    String? shanghaiDate,
  }) async {
    final uri = _uri('/api/practice/records', {
      'page': page,
      'page_size': pageSize,
      if (shanghaiDate != null && shanghaiDate.isNotEmpty)
        'shanghai_date': shanghaiDate,
    });
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return PracticeRecordFeedPage.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSession> startPracticeSession(
      String? category, int count) async {
    final query = {'count': count, if (category != null) 'category': category};
    final uri = _uri('/api/practice/sessions/start', query);
    final res =
        await _guardedRequest(() => http.post(uri), uri: uri, method: 'POST');
    _check(res);
    return PracticeSession.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSession> startPracticeSessionCustom(
      List<int> questionIds) async {
    final uri = _uri('/api/practice/sessions/start/custom');
    final res = await _guardedRequest(
      () => http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question_ids': questionIds}),
      ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return PracticeSession.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSubmitResult> submitPracticeAnswer(
      int sessionId, int questionId, String userAnswer) async {
    final uri = _uri('/api/practice/sessions/$sessionId/submit');
    final res = await _guardedRequest(
      () => http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body:
            jsonEncode({'question_id': questionId, 'user_answer': userAnswer}),
      ),
      uri: uri,
      method: 'POST',
    );
    _check(res);
    return PracticeSubmitResult.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSubmitResult> skipPracticeAnswer(
      int sessionId, int questionId) async {
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
    return PracticeSubmitResult.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  Future<PracticeSummary> fetchPracticeSummary(int sessionId) async {
    final uri = _uri('/api/practice/sessions/$sessionId/summary');
    final res =
        await _guardedRequest(() => http.get(uri), uri: uri, method: 'GET');
    _check(res);
    return PracticeSummary.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
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
    if (stackTrace != null) {
      buf.writeln('stack: ${_shorten(stackTrace.toString(), 1200)}');
    }
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
    required this.referenceAnswer,
    required this.createdAt,
  });

  final int id;
  final String stem;
  final String category;
  final int difficulty;
  final int masteryScore;
  final String referenceAnswer;
  final String createdAt;

  String get difficultyStars {
    final n = difficulty.clamp(1, 5);
    return '${'★' * n}${'☆' * (5 - n)}';
  }

  factory QuestionItem.fromJson(Map<String, dynamic> json) => QuestionItem(
        id: json['id'] as int,
        stem: json['stem'] as String,
        category: json['category'] as String,
        difficulty: json['difficulty'] as int,
        masteryScore: json['mastery_score'] as int? ?? 0,
        referenceAnswer: (json['reference_answer'] as String?) ?? '',
        createdAt: (json['created_at'] as String?) ?? '',
      );
}

class QuestionPage {
  QuestionPage(
      {required this.total,
      required this.page,
      required this.pageSize,
      required this.items});
  final int total;
  final int page;
  final int pageSize;
  final List<QuestionItem> items;

  factory QuestionPage.fromJson(Map<String, dynamic> json) => QuestionPage(
        total: json['total'] as int? ?? 0,
        page: json['page'] as int? ?? 1,
        pageSize: json['page_size'] as int? ?? 20,
        items: (json['items'] as List<dynamic>? ?? const [])
            .map((e) => QuestionItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PracticeCategory {
  PracticeCategory(
      {required this.category,
      required this.totalQuestions,
      required this.selectable});
  final String category;
  final int totalQuestions;
  final bool selectable;

  factory PracticeCategory.fromJson(Map<String, dynamic> json) =>
      PracticeCategory(
        category: json['category'] as String,
        totalQuestions: json['total_questions'] as int,
        selectable: json['selectable'] as bool,
      );
}

class PracticeActivityDay {
  PracticeActivityDay(
      {required this.date, required this.count, required this.level});
  final String date;
  final int count;
  final int level;

  factory PracticeActivityDay.fromJson(Map<String, dynamic> json) =>
      PracticeActivityDay(
        date: json['date'] as String? ?? '',
        count: json['count'] as int? ?? 0,
        level: json['level'] as int? ?? 0,
      );
}

class PracticeActivityResponse {
  PracticeActivityResponse({
    required this.today,
    required this.totalQuestions,
    required this.activeDays,
    required this.days,
  });
  final String today;
  final int totalQuestions;
  final int activeDays;
  final List<PracticeActivityDay> days;

  factory PracticeActivityResponse.fromJson(Map<String, dynamic> json) =>
      PracticeActivityResponse(
        today: json['today'] as String? ?? '',
        totalQuestions: json['total_questions'] as int? ?? 0,
        activeDays: json['active_days'] as int? ?? 0,
        days: (json['days'] as List<dynamic>? ?? const [])
            .map((e) => PracticeActivityDay.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PracticeSessionListItem {
  PracticeSessionListItem({
    required this.id,
    required this.totalScore,
    required this.questionCount,
    required this.completedAt,
  });
  final int id;
  final int totalScore;
  final int questionCount;
  final String? completedAt;

  factory PracticeSessionListItem.fromJson(Map<String, dynamic> json) =>
      PracticeSessionListItem(
        id: json['id'] as int? ?? 0,
        totalScore: json['total_score'] as int? ?? 0,
        questionCount: json['question_count'] as int? ?? 10,
        completedAt: json['completed_at'] as String?,
      );
}

class PracticeSession {
  PracticeSession({required this.sessionId, required this.questions});
  final int sessionId;
  final List<QuestionItem> questions;

  factory PracticeSession.fromJson(Map<String, dynamic> json) =>
      PracticeSession(
        sessionId: json['session_id'] as int,
        questions: (json['questions'] as List<dynamic>)
            .map((e) => QuestionItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PracticeSubmitResult {
  PracticeSubmitResult(
      {required this.score,
      required this.analysis,
      required this.referenceAnswer});
  final int score;
  final String analysis;
  final String referenceAnswer;

  factory PracticeSubmitResult.fromJson(Map<String, dynamic> json) =>
      PracticeSubmitResult(
        score:
            ((json['record'] as Map<String, dynamic>?)?['ai_score'] as int?) ??
                0,
        analysis: json['analysis'] as String,
        referenceAnswer: json['reference_answer'] as String? ?? '',
      );
}

class PracticeRecordItem {
  PracticeRecordItem({
    required this.id,
    required this.userAnswer,
    required this.aiAnswer,
    required this.aiScore,
    required this.createdAt,
  });
  final int id;
  final String userAnswer;
  final String aiAnswer;
  final int aiScore;
  final String createdAt;

  factory PracticeRecordItem.fromJson(Map<String, dynamic> json) =>
      PracticeRecordItem(
        id: json['id'] as int,
        userAnswer: (json['user_answer'] as String?) ?? '',
        aiAnswer: (json['ai_answer'] as String?) ?? '',
        aiScore: (json['ai_score'] as int?) ?? 0,
        createdAt: (json['created_at'] as String?) ?? '',
      );
}

class PracticeSummary {
  PracticeSummary({
    required this.sessionId,
    required this.totalScore,
    required this.recordIds,
    required this.questionCount,
  });
  final int sessionId;
  final int totalScore;
  final List<int> recordIds;
  final int questionCount;

  factory PracticeSummary.fromJson(Map<String, dynamic> json) =>
      PracticeSummary(
        sessionId: json['session_id'] as int? ?? 0,
        totalScore: json['total_score'] as int,
        recordIds: (json['record_ids'] as List<dynamic>? ?? const [])
            .map((e) => e as int)
            .toList(),
        questionCount: json['question_count'] as int? ?? 10,
      );
}

class PracticeSessionRecordsResponse {
  PracticeSessionRecordsResponse({
    required this.totalScore,
    required this.questionCount,
    required this.completedAt,
    required this.records,
  });
  final int totalScore;
  final int questionCount;
  final String? completedAt;
  final List<PracticeRecordItem> records;

  factory PracticeSessionRecordsResponse.fromJson(Map<String, dynamic> json) =>
      PracticeSessionRecordsResponse(
        totalScore: json['total_score'] as int? ?? 0,
        questionCount: json['question_count'] as int? ?? 10,
        completedAt: json['completed_at'] as String?,
        records: (json['records'] as List<dynamic>? ?? const [])
            .map((e) => PracticeRecordItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PracticeRecordFeedItem {
  PracticeRecordFeedItem({
    required this.id,
    required this.sessionId,
    required this.questionStem,
    required this.userAnswer,
    required this.aiAnswer,
    required this.aiScore,
    required this.createdAt,
  });
  final int id;
  final int? sessionId;
  final String questionStem;
  final String userAnswer;
  final String aiAnswer;
  final int aiScore;
  final String createdAt;

  factory PracticeRecordFeedItem.fromJson(Map<String, dynamic> json) =>
      PracticeRecordFeedItem(
        id: json['id'] as int? ?? 0,
        sessionId: json['session_id'] as int?,
        questionStem: json['question_stem'] as String? ?? '',
        userAnswer: json['user_answer'] as String? ?? '',
        aiAnswer: json['ai_answer'] as String? ?? '',
        aiScore: json['ai_score'] as int? ?? 0,
        createdAt: json['created_at'] as String? ?? '',
      );
}

class PracticeRecordFeedPage {
  PracticeRecordFeedPage({required this.total, required this.items});
  final int total;
  final List<PracticeRecordFeedItem> items;

  factory PracticeRecordFeedPage.fromJson(Map<String, dynamic> json) =>
      PracticeRecordFeedPage(
        total: json['total'] as int? ?? 0,
        items: (json['items'] as List<dynamic>? ?? const [])
            .map((e) =>
                PracticeRecordFeedItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
