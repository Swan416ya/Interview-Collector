"""
入库：最近模拟面试里尚未单独成题的知识点 + 若干 Vue / JavaScript / CSS 题（分类统一为「前端」）。
按 stem 全文去重，已存在则跳过。

运行：
  backend\\.venv\\Scripts\\python.exe scripts\\insert_recent_interview_and_frontend_questions.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.question import Question
from app.models.taxonomy import Category
from app.services.kb_chunk_service import sync_question_chunks

questions: list[dict[str, str | int]] = [
    # --- 最近模拟面试补题（与淘天面经题干区分，避免 stem 完全一致）---
    {
        "stem": "MySQL InnoDB 默认使用哪种事务隔离级别？为什么常用这个级别？",
        "category": "MySQL",
        "difficulty": 2,
        "reference_answer": (
            "默认是 REPEATABLE READ（可重复读）。\n"
            "InnoDB 在该级别下通过 MVCC、记录锁、间隙锁（Gap Lock）、临键锁（Next-Key Lock）等机制，"
            "在很大程度上抑制幻读等并发问题，同时相比 SERIALIZABLE 仍保留较好并发度。\n"
            "注意：SQL 标准下 RR 仍可能出现幻读语义争议；InnoDB 的实现通常被称为在 RR 下对幻读做了工程化控制。"
        ),
    },
    {
        "stem": "如何预防死锁？请结合死锁的四个必要条件分别说明可采取的策略。",
        "category": "操作系统",
        "difficulty": 3,
        "reference_answer": (
            "死锁四条件：互斥、占有且等待、不可剥夺、循环等待。\n"
            "1. 破坏互斥：少数资源可设计为可共享（多数锁场景难以去掉互斥）。\n"
            "2. 破坏占有且等待：一次性申请全部资源；或 tryLock 拿不到就释放已占有资源。\n"
            "3. 破坏不可剥夺：使用可超时/可升级的锁；或允许抢占（需业务支持）。\n"
            "4. 破坏循环等待：全局统一加锁顺序；按资源 ID 排序申请。\n"
            "数据库场景还可通过降低事务粒度、合理索引减少锁范围、死锁检测与回滚等处理。"
        ),
    },
    {
        "stem": "请简述 JVM 运行时数据区包含哪些部分，并说明哪些是线程私有、哪些是线程共享。",
        "category": "Java",
        "difficulty": 3,
        "reference_answer": (
            "线程私有：程序计数器；Java 虚拟机栈；本地方法栈。\n"
            "线程共享：堆（对象实例、数组，GC 主要区域）；方法区（JDK8+ 元空间 Metaspace，类元数据、常量池等）；运行时常量池（逻辑上属方法区）；直接内存（如 NIO，堆外）。\n"
            "易混点：口语中的「JVM 内存模型」有时也指 JMM（Java Memory Model，与并发可见性/有序性相关），与运行时数据区不是同一概念，面试可先澄清。"
        ),
    },
    {
        "stem": "操作系统中分段（segmentation）与分页（paging）的主要区别是什么？各有什么优缺点？",
        "category": "操作系统",
        "difficulty": 3,
        "reference_answer": (
            "分段：按程序逻辑模块划分，段长可变；地址为段号+段内偏移；利于共享与保护；易产生外部碎片。\n"
            "分页：物理划分为固定大小的页框，逻辑页与页框对齐；地址为页号+页内偏移；无外部碎片（或有少量内部碎片）；便于非连续分配与换入换出。\n"
            "段页式：先分段再段内分页，结合二者优点，实现更复杂。\n"
            "现代系统常见多级页表 + TLB 加速地址翻译。"
        ),
    },
    # --- Vue ---
    {
        "stem": "Vue 中 computed 和 watch 的区别是什么？各自适合什么场景？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "computed：基于响应式依赖做派生值，带缓存，只有依赖变化时才重新计算；适合「由已有状态计算出的展示值」。\n"
            "watch：监听某个数据源变化后执行副作用（异步请求、DOM、日志等）；适合「数据变化后要做事」而非单纯派生。\n"
            "Vue3 还可使用 watchEffect 自动收集依赖执行副作用。\n"
            "选用原则：能 computed 表达优先 computed，逻辑复杂或异步用 watch。"
        ),
    },
    {
        "stem": "Vue 中的 nextTick 有什么作用？在什么场景下会用到？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "作用：在下次 DOM 更新周期之后执行回调，确保读到的是更新后的 DOM。\n"
            "原因：Vue 对同一轮中的数据变更做批量异步更新，数据修改后立刻读 DOM 可能仍是旧视图。\n"
            "典型场景：修改数据后需要测量新布局、聚焦输入框、基于新 DOM 做第三方库初始化等。\n"
            "实现上通常基于微任务（Promise）或 MutationObserver，具体随版本/runtime 略有差异。"
        ),
    },
    {
        "stem": "Vue 3 组合式 API 中 ref 与 reactive 的主要区别是什么？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "ref：可包装任意类型，基本类型也会变成响应式；在 script 中通过 .value 访问/修改；模板中自动解包。\n"
            "reactive：只接受对象类型（含数组、Map 等），返回 Proxy；属性访问无需 .value。\n"
            "解构陷阱：reactive 对象直接解构会丢失响应式，需 toRefs；ref 解构可用 storeToRefs（Pinia）等模式。\n"
            "实践：单一标量或可能整体替换的用 ref；复杂对象状态机可用 reactive。"
        ),
    },
    # --- JavaScript ---
    {
        "stem": "JavaScript 中的原型链是什么？对象读取属性时的查找顺序是怎样的？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "每个对象有隐式原型 __proto__（标准访问可用 Object.getPrototypeOf），指向其构造函数的 prototype。\n"
            "查找属性时：先在对象自身属性找；没有则沿原型链向上查找，直到 Object.prototype 再往上为 null。\n"
            "hasOwnProperty 与 in 运算符区别：前者只看自有属性，后者包含原型链上的可枚举属性。\n"
            "ES6 class 语法糖底层仍是原型继承。"
        ),
    },
    {
        "stem": "Promise.all 与 Promise.race 的区别和使用场景分别是什么？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "Promise.all：入参为可迭代 Promise 列表，全部成功才 resolve，结果为与入参顺序一致的结果数组；任一 reject 则立刻 reject（常称「快速失败」）。\n"
            "适用：并行请求多个独立接口且都成功才算完成。\n"
            "Promise.race：第一个 settled（成功或失败）的 Promise 决定结果。\n"
            "适用：超时控制、多个数据源竞速取先返回者等。\n"
            "补充：Promise.allSettled 等待全部结束不论成败；Promise.any 取首个成功。"
        ),
    },
    {
        "stem": "什么是 JavaScript 的防抖（debounce）与节流（throttle）？各举一个适用场景。",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "防抖：在连续触发中，只在最后一次触发后延迟执行；若延迟期内再次触发则重新计时。\n"
            "场景：搜索框输入联想、窗口 resize 结束后布局计算。\n"
            "节流：固定时间窗口内最多执行一次，中间触发被丢弃或合并到下一次窗口。\n"
            "场景：滚动监听、鼠标移动绘制、高频上报限流。\n"
            "二者都用于控制高频事件成本，选择取决于「要等停顿」还是「要固定频率采样」。"
        ),
    },
    # --- CSS / 前端 ---
    {
        "stem": "CSS Flex 布局中 justify-content 与 align-items 分别控制哪个方向上的对齐？",
        "category": "前端",
        "difficulty": 1,
        "reference_answer": (
            "默认 flex-direction: row 时：\n"
            "- justify-content：控制主轴（main axis，横向）上子项的分布与对齐，如 flex-start、center、space-between。\n"
            "- align-items：控制交叉轴（cross axis，纵向）上子项在行内的对齐，如 stretch、center、flex-start。\n"
            "当 flex-direction: column 时，主轴与交叉轴互换，justify-content 管纵向、align-items 管横向。\n"
            "多行时用 align-content 控制行与行之间在交叉轴上的分布。"
        ),
    },
    {
        "stem": "CSS 选择器优先级（权重）如何比较？!important、行内样式、ID、类、标签的大致关系？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "层叠规则：来源与重要性（!important + 作者/用户/浏览器默认）> 特异性（Specificity）> 源码顺序（后写覆盖先写，同特异性时）。\n"
            "特异性常见估算（简化记忆）：行内 style 最高；其次 ID；再次类/属性/伪类；再标签/伪元素。\n"
            "例如：#id .class 高于 .class div。\n"
            "!important 可压过普通特异性比较，但仍参与层叠；滥用会降低可维护性。\n"
            "实际排查可用开发者工具查看哪条规则生效及被划掉的原因。"
        ),
    },
    {
        "stem": "CSS 中 position: relative / absolute / fixed / sticky 各自如何定位？包含块（containing block）通常是谁？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "relative：相对自身正常文档流位置偏移，不脱离文档流；常作 absolute 子元素的定位参照。\n"
            "absolute：脱离文档流，相对最近的非 static 定位祖先（若无则视口/初始包含块）偏移。\n"
            "fixed：相对视口（viewport）固定，滚动一般不跟随；移动端需注意变换祖先可能创建新包含块。\n"
            "sticky：在滚动阈值前类似 relative，之后类似 fixed 粘在容器内；需指定 top/left 等阈值，父 overflow 非 visible 时易失效。\n"
            "包含块决定百分比与绝对定位参照，面试能说清「找最近的定位祖先」即可。"
        ),
    },
    # --- 前端补充（偏基础，难度 1–2）---
    {
        "stem": "Vue 中 v-if 和 v-show 的区别是什么？各自更适合什么场景？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "v-if：条件为假时不渲染 DOM，切换开销在创建/销毁组件；适合条件很少成立或子组件很重的情况。\n"
            "v-show：始终渲染，用 CSS（display）切换显隐；适合频繁切换显示状态。\n"
            "记忆：要省 DOM 用 v-if，要省切换成本用 v-show。"
        ),
    },
    {
        "stem": "Vue 列表渲染（v-for）里为什么要写 key？用 index 当 key 可能有什么问题？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "key 帮助框架识别每个节点的身份，diff 时能复用 DOM、减少错位更新。\n"
            "用数组下标当 key：列表中间插入/删除/排序时，下标会变化，导致错误复用，输入框内容错位、动画异常等。\n"
            "优先使用稳定且唯一的业务 id 作为 key。"
        ),
    },
    {
        "stem": "JavaScript 中 == 和 === 的区别是什么？日常更推荐用哪个？",
        "category": "前端",
        "difficulty": 1,
        "reference_answer": (
            "== 会做类型转换再比较（隐式转换规则多，容易踩坑）；=== 不做类型转换，类型不同直接为 false。\n"
            "日常推荐几乎总是用 ===，代码意图更清晰、更少意外相等。\n"
            "例外：少数库接口或历史代码会刻意用 ==，新代码尽量避免。"
        ),
    },
    {
        "stem": "表达式 typeof null 在 JavaScript 中的结果是什么？为什么常被说成历史遗留问题？",
        "category": "前端",
        "difficulty": 1,
        "reference_answer": (
            "结果是字符串 \"object\"。\n"
            "原因是早期实现里值的类型标记与 null 的表示方式导致 typeof 把它归成 object，后来为兼容一直未改。\n"
            "判断 null 请用 value === null。"
        ),
    },
    {
        "stem": "浏览器中 localStorage 和 sessionStorage 的主要区别是什么？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "作用域：同源下 localStorage 各标签页可共享（同源策略）；sessionStorage 通常只在当前标签页会话内有效，关闭标签即清空。\n"
            "持久性：localStorage 除非手动清除否则会一直保留；sessionStorage 随会话结束清除。\n"
            "二者都是字符串键值、容量有限（约数 MB，因浏览器而异），不适合存敏感信息。"
        ),
    },
    {
        "stem": "DOM 事件流中捕获阶段和冒泡阶段的大致顺序是什么？addEventListener 第三个参数有什么用？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "顺序：从 window 向下到目标为捕获阶段，再从目标向上冒泡到 window 为冒泡阶段（目标阶段在两者之间）。\n"
            "addEventListener(type, fn, useCapture)：第三个参数为 true 时在捕获阶段触发，false（默认）在冒泡阶段触发。\n"
            "旧版曾用 attachEvent 等，现代统一用 addEventListener。"
        ),
    },
    {
        "stem": "event.preventDefault() 和 event.stopPropagation() 分别做什么？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "preventDefault：阻止浏览器对该事件的默认行为（如表单 submit、a 标签跳转、触摸滚动等）。\n"
            "stopPropagation：阻止事件继续向捕获/冒泡方向传播，父级监听器收不到该事件。\n"
            "二者独立：可以只阻止默认、只阻止传播，或同时使用。"
        ),
    },
    {
        "stem": "使用 HTML 语义化标签（如 header、nav、main、article）有什么好处？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "可读性与维护：结构一眼能看懂页面区域。\n"
            "无障碍：读屏软件更好理解文档结构。\n"
            "SEO：搜索引擎更好理解内容层次（辅助，非唯一因素）。\n"
            "样式上语义标签默认与 div 一样可通过 CSS 控制外观。"
        ),
    },
    {
        "stem": "CSS 中 rem 和 em 有什么区别？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "rem：相对于根元素 html 的 font-size，全站统一缩放方便（如根字号 62.5% 做 10px 基准）。\n"
            "em：相对于当前元素的 font-size，会层层继承/相乘，嵌套过深时容易算不清。\n"
            "布局与响应式常用 rem；局部相对父字号排版可用 em。"
        ),
    },
    {
        "stem": "相邻块级元素的上下 margin 有时会「合并」成一条边距，大致原因和常见规避方式是什么？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "称为 margin collapse（外边距折叠），垂直相邻的块级盒在特定条件下会取较大 margin 而不是相加。\n"
            "常见规避：给父元素加 padding/border、触发 BFC（如 overflow: hidden）、用 flex 子项代替纯块级流布局等。\n"
            "水平 margin 一般不折叠。"
        ),
    },
    {
        "stem": "script 标签上的 async 和 defer 属性有什么区别？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "二者都会并行下载脚本，不阻塞 HTML 解析（与默认同步阻塞不同）。\n"
            "defer：下载完后等 HTML 解析完成再按顺序执行脚本，适合依赖 DOM 的普通脚本。\n"
            "async：下载完尽快执行，顺序不保证，适合独立统计脚本等。\n"
            "都没有时：脚本下载与执行都会阻塞解析。"
        ),
    },
    {
        "stem": "HTML 里行内元素（inline）和块级元素（block）各说两个典型区别。",
        "category": "前端",
        "difficulty": 1,
        "reference_answer": (
            "块级：独占一行（默认可设 width/height、上下 margin 生效明显）；常见如 div、p、h1。\n"
            "行内：可与文字同行、width/height 默认不生效（对替换元素如 img 例外）、垂直 margin 常不生效；常见如 span、a。\n"
            "inline-block 介于两者之间：同行显示又可设宽高。"
        ),
    },
    {
        "stem": "CSS 中 z-index 在什么情况下才会生效？什么是层叠上下文（stacking context）的粗浅理解？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "z-index 只对定位元素等有效：position 非 static，或 flex/grid 子项等浏览器规定的场景。\n"
            "层叠上下文：一组元素在 z 轴上比较先后绘制；新建上下文的常见条件包括 position+ z-index、opacity<1、transform、filter 等。\n"
            "不同层叠上下文之间先比父级，再比内部 z-index，不能跨上下文简单用数值对齐。"
        ),
    },
]


def _ensure_taxonomy_categories(db, names: set[str]) -> None:
    existing = set(db.scalars(select(Category.name)).all())
    for name in sorted(names):
        if name not in existing:
            db.add(Category(name=name))
            existing.add(name)
            print(f"[taxonomy] + Category {name!r}")


def main() -> None:
    db = SessionLocal()
    try:
        cats = {str(q["category"]) for q in questions}
        _ensure_taxonomy_categories(db, cats)

        inserted = 0
        skipped = 0
        for q_data in questions:
            stem = str(q_data["stem"])
            existing = db.scalars(select(Question).where(Question.stem == stem)).first()
            if existing is not None:
                print(f"SKIP: {stem[:56]}...")
                skipped += 1
                continue
            q = Question(
                stem=stem,
                category=str(q_data["category"]),
                difficulty=int(q_data["difficulty"]),
                reference_answer=str(q_data["reference_answer"]),
            )
            db.add(q)
            db.flush()
            sync_question_chunks(db, q)
            inserted += 1
            print(f"OK: {stem[:56]}...")
        db.commit()
        total_n = int(db.scalar(select(func.count()).select_from(Question)) or 0)
        print(f"\nInserted={inserted}, Skipped={skipped}, Total questions={total_n}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
