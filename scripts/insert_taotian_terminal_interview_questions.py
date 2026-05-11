"""
Insert 淘天终端 一面 面经题目（用户提供的真实面试题列表）到 questions 表。
重复 stem 会跳过。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import SessionLocal
from app.models.question import Question
from app.services.kb_chunk_service import sync_question_chunks

SOURCE_TAG = "面经-淘天终端"

questions = [
    {
        "stem": f"【{SOURCE_TAG}】请做自我介绍（技术面可如何组织内容）。",
        "category": "综合",
        "difficulty": 1,
        "reference_answer": (
            "技术面自我介绍建议控制在1-2分钟，包含：\n"
            "1. 教育背景与方向（学校、专业、毕业时间）\n"
            "2. 技术栈与岗位匹配点（如终端：JS/TS、Vue/React、移动端或跨端等）\n"
            "3. 1-2个代表性项目：背景、你的职责、技术难点与结果（量化更好）\n"
            "4. 结尾表达岗位兴趣与可实习时间\n"
            "避免流水账，突出与「终端/工程」相关的经历。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】数组和链表的区别是什么？",
        "category": "数据结构",
        "difficulty": 2,
        "reference_answer": (
            "存储结构：数组在内存中连续分配，链表通过指针（引用）连接离散节点。\n"
            "随机访问：数组按下标 O(1)；链表需遍历 O(n)。\n"
            "插入删除：数组中间操作需搬移元素，平均 O(n)；链表已知位置插入删除 O(1)。\n"
            "空间：数组可能预分配浪费或扩容拷贝；链表每个节点额外存储指针，有内存碎片问题。\n"
            "缓存友好性：数组顺序访问对 CPU 缓存更友好；链表跳转访问缓存命中率低。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】Java 中接口（interface）和抽象类（abstract class）的区别？",
        "category": "Java",
        "difficulty": 2,
        "reference_answer": (
            "继承：类单继承抽象类；可实现多个接口。\n"
            "成员：接口 JDK8 前只能常量和抽象方法；JDK8+ 可有 default/static 方法；JDK9+ 可有 private 方法。"
            "抽象类可有任意访问修饰的成员、构造方法、状态字段。\n"
            "设计语义：抽象类表达「is-a」的共性骨架；接口表达「can-do」的能力契约。\n"
            "实例化：都不能直接 new，需子类实现/继承后实例化。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】什么是进程（process）？什么是线程（thread）？二者关系？",
        "category": "操作系统",
        "difficulty": 2,
        "reference_answer": (
            "进程：资源分配与调度的基本单位，拥有独立地址空间、文件描述符、打开文件等。\n"
            "线程：CPU 调度的基本单位，共享所属进程的地址空间与大部分资源，有独立栈、寄存器、程序计数器。\n"
            "关系：线程依附于进程；同一进程内多线程共享堆、代码段、数据段等，通信成本低但需同步。\n"
            "对比：进程切换开销大、隔离性好；线程切换相对轻量，但共享内存易出竞态。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】死锁产生的必要条件有哪些？",
        "category": "操作系统",
        "difficulty": 2,
        "reference_answer": (
            "Coffman 四必要条件（同时满足才可能死锁）：\n"
            "1. 互斥：资源不能被多个线程同时使用。\n"
            "2. 占有且等待：已占有一部分资源的同时等待其它资源。\n"
            "3. 不可抢占：已分配资源只能由持有者显式释放。\n"
            "4. 循环等待：存在资源的循环等待链。\n"
            "破坏任一条件可预防/避免死锁；检测则可用资源分配图等。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】简述 JVM 运行时内存区域（或常被口语称为「JVM 内存模型」的堆栈划分）。",
        "category": "Java",
        "difficulty": 3,
        "reference_answer": (
            "注意：口语「JVM 内存模型」有时指运行时数据区，有时指 JMM（Java Memory Model，并发内存语义）。面试可先澄清。\n\n"
            "运行时数据区常见划分：\n"
            "1. 程序计数器：当前线程执行字节码行号。\n"
            "2. Java 虚拟机栈：栈帧（局部变量表、操作数栈等），线程私有。\n"
            "3. 本地方法栈：Native 方法服务。\n"
            "4. 堆：对象实例、数组，线程共享，GC 主要区域。\n"
            "5. 方法区（JDK8+ 元空间 Metaspace，使用本地内存）：类信息、常量、静态变量、JIT 代码等。\n"
            "6. 直接内存：NIO 等使用的堆外内存。\n\n"
            "JMM：主内存与工作内存、happens-before、volatile 可见性有序性等，与并发相关。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】Java 垃圾回收（GC）机制大致是怎样的？",
        "category": "Java",
        "difficulty": 3,
        "reference_answer": (
            "目标：自动回收堆中不再被引用的对象，防止内存泄漏。\n"
            "判断存活：可达性分析（从 GC Roots 出发），非引用计数。\n"
            "GC Roots 示例：栈上引用、静态引用、常量池引用、JNI 引用、同步锁持有对象等。\n"
            "分代假说：大部分对象朝生夕死；跨代引用相对较少。Young Gen（Eden/S0/S1）+ Old Gen 等。\n"
            "常见收集器思路：Serial、Parallel、CMS、G1、ZGC 等（分代/分区、并发标记、停顿时间目标不同）。\n"
            "调优方向：停顿 vs 吞吐、堆大小、晋升阈值、避免大对象与内存泄漏等。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】Java 类加载过程大致分哪几个阶段？",
        "category": "Java",
        "difficulty": 3,
        "reference_answer": (
            "整体：加载 -> 链接（验证、准备、解析）-> 初始化 ->（使用）-> 卸载。\n"
            "加载：通过全限定名获取二进制字节流，在方法区生成 Class 元数据，堆中生成 java.lang.Class 对象。\n"
            "验证：文件格式、元数据、字节码、符号引用等合法性检查。\n"
            "准备：为类变量分配内存并赋零值（非 final static 在此阶段为默认值）。\n"
            "解析：符号引用转直接引用（可选时机）。\n"
            "初始化：执行 <clinit>，初始化 static 块与 static 字段赋值。\n"
            "双亲委派：类加载器委派模型，保证核心类库安全与唯一性。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】红黑树的特点是什么？与 AVL 相比如何？",
        "category": "数据结构",
        "difficulty": 3,
        "reference_answer": (
            "红黑树是自平衡 BST，通过染色与旋转保持近似平衡，保证最坏高度 O(log n)。\n"
            "性质要点：根黑；红节点子必黑；从任一节点到叶子的黑高相同；叶（NIL）视为黑。\n"
            "与 AVL：AVL 更严格平衡，查找略快但旋转更多；红黑树插入删除常数更好，工程里更常用（如 HashMap 树化）。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】操作系统中分段（segmentation）与分页（paging）的区别？",
        "category": "操作系统",
        "difficulty": 3,
        "reference_answer": (
            "分段：按程序逻辑模块划分，段长可变，二维地址（段号+段内偏移）；利于共享与保护，易产生外部碎片。\n"
            "分页：物理划分固定大小页框，逻辑页大小与页框对齐，一维页号+页内偏移；内部碎片、无外部碎片（或交换区管理）。\n"
            "段页式：先分段再段内分页，结合二者优点，实现更复杂。\n"
            "现代 OS 常见多级页表、TLB 加速地址翻译。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】TCP 与 UDP 的区别？TCP 在 OSI 七层模型中位于哪一层？",
        "category": "计算机网络",
        "difficulty": 2,
        "reference_answer": (
            "TCP：面向连接、可靠传输（序号确认、重传、流量控制、拥塞控制）、全双工、字节流；头部较大；适用 HTTP、RPC 等。\n"
            "UDP：无连接、尽力交付、不保证顺序与可靠、头部小、实时性更好；适用 DNS、音视频、游戏状态等。\n"
            "OSI：二者均在第 4 层传输层（Transport Layer）。\n"
            "注意：实际工程常对照 TCP/IP 五层/四层模型，传输层对应 OSI 第四层。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】HTTP 与 HTTPS 的区别？",
        "category": "计算机网络",
        "difficulty": 2,
        "reference_answer": (
            "HTTPS = HTTP + TLS/SSL 加密与身份校验。\n"
            "端口：HTTP 常用 80，HTTPS 常用 443。\n"
            "安全：HTTPS 防窃听、防篡改，依赖数字证书链校验服务器身份；协商会话密钥后对称加密传输。\n"
            "性能：HTTPS 多一次握手开销，但有会话复用、TLS1.3 0-RTT 等优化。\n"
            "SEO/浏览器：现代浏览器对 HTTPS 更友好。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】ping 命令底层主要使用什么协议？",
        "category": "计算机网络",
        "difficulty": 2,
        "reference_answer": (
            "ICMP（Internet Control Message Protocol），网际控制报文协议。\n"
            "ping 通常发送 ICMP Echo Request，对端回复 ICMP Echo Reply。\n"
            "用于连通性探测、时延与丢包粗测；可能被防火墙或云安全策略禁用。\n"
            "注意：ICMP 工作在网络层（TCP/IP 模型），封装在 IP 数据报中。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】介绍 TCP 三次握手过程及作用。",
        "category": "计算机网络",
        "difficulty": 2,
        "reference_answer": (
            "1) 客户端发 SYN，携带初始序列号 seq=x，进入 SYN_SENT。\n"
            "2) 服务端回 SYN+ACK，seq=y，ack=x+1，进入 SYN_RCVD。\n"
            "3) 客户端发 ACK，ack=y+1，双方进入 ESTABLISHED。\n"
            "作用：同步双方初始序列号；确认双方收发能力；防止历史重复连接请求造成错误建立。\n"
            "为什么是三次：两次无法让发送方确认对方已收到自己的确认，且易受延迟 SYN 影响。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】若有一亿条数据，如何快速查找某条记录？可按场景举例。",
        "category": "MySQL",
        "difficulty": 4,
        "reference_answer": (
            "先澄清查询条件：按主键/唯一 id、按业务唯一键、还是全文/关键词检索。\n\n"
            "通用思路：\n"
            "1. 分库分表：按用户 id、时间、地域等 sharding key 水平拆分，单表数据量可控，减少扫描范围。\n"
            "2. 按主键/唯一键：B+ 树聚簇索引（InnoDB 主键即聚簇索引），点查 O(log n) 级别页访问。\n"
            "3. 关键词搜索：倒排索引（Elasticsearch 等）或数据库全文索引，适合非结构化文本检索。\n"
            "4. 热点与缓存：Redis 等缓存热点键；布隆过滤器防穿透（需场景匹配）。\n"
            "5. 归档与冷热分层：老数据迁出，减小在线库体量。\n\n"
            "面经提示：关键词依赖倒排索引；按 id 走聚簇/二级索引。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】MySQL 事务隔离级别有哪些？分别解决什么问题？",
        "category": "MySQL",
        "difficulty": 3,
        "reference_answer": (
            "（面经补充：可能追问事务与索引）\n"
            "四个隔离级别（从低到高）：\n"
            "1. READ UNCOMMITTED：可能脏读、不可重复读、幻读。\n"
            "2. READ COMMITTED：避免脏读；仍可能不可重复读、幻读（Oracle/SQL Server 常用）。\n"
            "3. REPEATABLE READ：避免脏读、不可重复读；InnoDB 下通过 MVCC+间隙锁等很大程度缓解幻读。\n"
            "4. SERIALIZABLE：串行化，最严格，并发最低。\n"
            "实现：MVCC、锁（记录锁、间隙锁、next-key）、undo log 版本链等。"
        ),
    },
    {
        "stem": f"【{SOURCE_TAG}】MySQL InnoDB 索引相关：聚簇索引与二级索引区别？常见优化思路？",
        "category": "MySQL",
        "difficulty": 3,
        "reference_answer": (
            "（面经补充：可能追问索引）\n"
            "聚簇索引：叶子节点存完整行数据；InnoDB 表必有聚簇索引，通常为主键。\n"
            "二级索引：叶子存主键值，回表查聚簇索引拿到整行（覆盖索引可避免回表）。\n"
            "B+ 树：有序、多路、叶子链表利于范围扫描；相比 B 树更适合磁盘页式读取。\n"
            "优化：合理最左前缀、避免索引失效（函数、隐式类型转换、like 前缀通配符等）、控制列区分度、分析执行计划。"
        ),
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for q_data in questions:
            existing = db.query(Question).filter(Question.stem == q_data["stem"]).first()
            if existing:
                print(f"SKIP: {q_data['stem'][:60]}...")
                skipped += 1
                continue
            q = Question(**q_data)
            db.add(q)
            db.flush()
            sync_question_chunks(db, q)
            inserted += 1
            print(f"OK: {q_data['stem'][:60]}...")
        db.commit()
        total = db.query(Question).count()
        print(f"\nInserted={inserted}, Skipped={skipped}, Total questions={total}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
