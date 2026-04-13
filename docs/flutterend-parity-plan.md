# Flutter 客户端与 Web 前端功能对齐计划

## 目标

让 `flutterend` 在**操作逻辑、功能覆盖、交互流程**上与 `frontend` 当前版本保持一致；视觉风格可继续保留移动端优化版本。

## 对齐范围（以 Web 前端为基准）

- 页面：`Home`、`Questions`、`Practice`、`PracticeHistory`、`AnswerRecords`
- 接口：`/api/questions*`、`/api/practice*`、`/api/categories`
- 核心流程：题库筛选分页/详情操作、练习模式、背题模式、每日一题、历史记录查看

---

## 里程碑与实现顺序

### Milestone 0：基础设施统一（先做）

- [ ] 统一 API 类型模型（Question / PracticeSession / PracticeRecord 等）
- [ ] 统一错误处理（状态码、detail、网络错误）
- [ ] 建立共享状态层（建议按页面拆 `ChangeNotifier` 或轻量状态容器）
- [ ] 路由结构扩展到 5 页签/入口（含历史页、答题记录页）

**验收标准**

- 所有 API 调用集中在 `api client`，页面不直接拼 JSON
- 错误提示格式统一，可定位到 URL + method + detail

---

### Milestone 1：题库页 `Questions` 对齐

对应 Web：`frontend/src/views/QuestionsView.vue`

- [x] 筛选：分类、难度、排序（recent/created/mastery）
- [x] 分页：页码切换 + pageSize（10/20/50/100）
- [x] 列表卡片展示：题干、分类、难度、掌握度、创建时间
- [ ] 题目详情弹层：
  - [x] 编辑题目
  - [x] 删除题目
  - [x] 刷新做题记录
  - [x] 刷新参考答案
  - [x] 单题独立判题（`daily/submit`）
  - [x] 历次得分趋势图
  - [x] 记录列表（用户答案/AI解析/时间）

**验收标准**

- 参数与 Web 一致：`sort_by/sort_order/page/page_size`
- 单题详情内操作全部可用，返回结果与 Web 同口径

---

### Milestone 2：训练中心 `Practice` 对齐

对应 Web：`frontend/src/views/PracticeView.vue`

- [x] 模式切换：刷题模式 / 背题模式
- [x] 题量：5 / 10 / 15
- [x] 分类约束与可用性检查（题量不足时禁用/报错）
- [x] 刷题模式：
  - [x] `start` 开局
  - [x] 提交判题
  - [x] 下一题自动 skip（未答）
  - [x] 结束后 summary 展示
- [x] 背题模式：
  - [x] 指定分类抽题学习（显示参考答案）
  - [x] 背题结束后乱序进入 custom 测验

**验收标准**

- 两种模式与 Web 流程一致
- 边界条件一致（题量不足、空答案、重复提交）

---

### Milestone 3：首页 `Home` 对齐

对应 Web：`frontend/src/views/HomeView.vue`

- [x] 用户信息卡（可先继续 mock）
- [x] 热力图（53 周、level 0-4 映射）
- [x] 刷题得分率趋势图（已完成 session）
- [x] 每日一题：
  - [x] 本地稳定选题（同一天同题）
  - [x] 今日是否已做检查
  - [x] 弹层答题 + 判题结果（解析/参考答案）

**验收标准**

- 热力图 count 与后端 activity 接口一致
- 每日一题当天刷新不变，跨天变化

---

### Milestone 4：历史页面对齐

对应 Web：
- `PracticeHistoryView.vue`
- `AnswerRecordsView.vue`

- [ ] 刷题记录页：
  - [ ] 会话列表
  - [ ] 会话详情弹层（总分、时间、题目记录）
- [ ] 答题记录页：
  - [ ] 全局记录分页
  - [ ] 日期筛选（`shanghai_date`）
  - [ ] 详情展开（完整题干、用户答案、AI解析）

**验收标准**

- 分页/筛选参数与 Web 一致
- 会话与记录详情数据字段完整

---

### Milestone 5：体验与回归

- [ ] 空态/加载态/错误态统一
- [ ] 大文本渲染（解析与参考答案，支持换行）
- [ ] Web 与 Android 调试地址文档复核
- [ ] 冒烟回归（5 大页面各一条完整链路）

**验收标准**

- 主要功能无阻断，页面间切换无状态错乱
- `flutter analyze` 无错误

---

## 建议实施节奏（一次一块）

1. 先做 Milestone 1（题库页）  
2. 再做 Milestone 2（训练中心）  
3. 再补 Milestone 3（首页）  
4. 最后 Milestone 4（历史页）  
5. 统一回归 Milestone 5

---

## 当前状态（本次建立文档时）

- 已有：基础三页壳子（首页/题库/练习）、部分 API 接入、移动端主题
- 未完成：与 Web 等价的完整功能逻辑（筛选分页、详情操作、背题模式、历史页等）

---

## 执行规则

- 每完成一个 Milestone，更新本文件勾选状态
- 每个 Milestone 完成后先本地验证，再进入下一项
- 若后端接口变更，必须同步更新此文档与 Flutter API 模型
