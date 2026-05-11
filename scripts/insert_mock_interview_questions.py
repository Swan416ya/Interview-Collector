"""
Insert mock interview questions into the database.
Questions from Alibaba terminal development intern interview simulation.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import SessionLocal
from app.models.question import Question
from app.services.kb_chunk_service import sync_question_chunks

questions = [
    {
        "stem": "JavaScript中var、let、const三者的区别是什么？从作用域、变量提升、是否可以重复声明等维度回答。",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "1. 作用域：var是函数作用域，let和const是块级作用域。\n"
            "2. 变量提升：三者都有变量提升，但let和const存在暂时性死区（TDZ），在声明之前访问会报ReferenceError；var提升后初始化为undefined。\n"
            "3. 重复声明：var可以重复声明，let和const不可以。\n"
            "4. 赋值：var和let可以重新赋值，const不可以（引用类型的内部属性可以修改）。\n"
            "实际开发中优先使用const，需要重新赋值时用let，避免使用var。"
        ),
    },
    {
        "stem": "什么是JavaScript闭包？闭包有哪些应用场景和需要注意的问题？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "闭包是指一个函数可以访问其词法作用域中的变量，即使这个函数在其外部作用域之外执行。简单说就是函数+它能访问到的外部变量环境。\n\n"
            "常见应用：\n"
            "1. 数据封装，模拟私有变量\n"
            "2. 函数工厂，比如写一个add(3)返回一个函数\n"
            "3. 回调函数和事件处理\n\n"
            "注意的问题：\n"
            "1. 可能造成内存泄漏，因为闭包持有的变量不会被垃圾回收\n"
            "2. 经典的for循环问题：用var的时候闭包里拿到的都是最终值，用let就没问题"
        ),
    },
    {
        "stem": "JavaScript的事件循环（Event Loop）机制是什么？宏任务和微任务的执行顺序是什么？分别举几个例子。",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "Event Loop是JS实现异步的机制。执行顺序：\n"
            "1. 同步代码先执行\n"
            "2. 执行完后清空微任务队列\n"
            "3. 取一个宏任务执行\n"
            "4. 再清空微任务队列\n"
            "5. 重复3、4\n\n"
            "优先级：同步 > 微任务 > 宏任务\n\n"
            "宏任务例子：setTimeout、setInterval、I/O、UI渲染\n"
            "微任务例子：Promise.then/catch/finally、MutationObserver、queueMicrotask\n\n"
            "经典面试题：\n"
            "console.log('1')\n"
            "setTimeout(() => console.log('2'), 0)\n"
            "Promise.resolve().then(() => console.log('3'))\n"
            "console.log('4')\n"
            "输出顺序：1、4、3、2"
        ),
    },
    {
        "stem": "HTTP常见状态码有哪些？401和403有什么区别？",
        "category": "计算机网络",
        "difficulty": 2,
        "reference_answer": (
            "常见状态码：\n"
            "1xx 信息性：100 Continue\n"
            "2xx 成功：200 OK、201 Created、204 No Content\n"
            "3xx 重定向：301 Moved Permanently（永久重定向）、302 Found（临时重定向）、304 Not Modified（协商缓存命中）\n"
            "4xx 客户端错误：400 Bad Request、401 Unauthorized、403 Forbidden、404 Not Found\n"
            "5xx 服务端错误：500 Internal Server Error、502 Bad Gateway、503 Service Unavailable\n\n"
            "401和403的区别：401表示未认证（你是谁），403表示已认证但无权限（你不配）。"
        ),
    },
    {
        "stem": "GET和POST请求有哪些区别？从多个维度对比说明。",
        "category": "计算机网络",
        "difficulty": 2,
        "reference_answer": (
            "GET vs POST 区别：\n"
            "1. 语义：GET获取资源，POST提交数据\n"
            "2. 参数位置：GET在URL中（query string），POST在请求体（body）中\n"
            "3. 幂等性：GET幂等（多次请求结果相同），POST非幂等\n"
            "4. 缓存：GET可被浏览器缓存，POST通常不缓存\n"
            "5. 书签：GET可以收藏为书签，POST不可以\n"
            "6. 参数长度：GET受URL长度限制（浏览器限制通常2KB~8KB），POST没有明确限制\n"
            "7. 编码类型：GET只支持URL编码，POST支持多种编码（JSON、form-data等）\n"
            "8. 安全性：GET参数暴露在URL中，相对不安全；POST参数在body中，相对安全\n\n"
            "注意：HTTP协议层面GET也可以传body，只是语义上不建议。"
        ),
    },
    {
        "stem": "TCP三次握手的过程是什么？为什么是三次而不是两次？",
        "category": "计算机网络",
        "difficulty": 3,
        "reference_answer": (
            "三次握手过程：\n"
            "1. 客户端发送SYN=1, seq=x，状态变为SYN_SENT\n"
            "2. 服务端发送SYN=1, ACK=1, seq=y, ack=x+1，状态变为SYN_RCVD\n"
            "3. 客户端发送ACK=1, seq=x+1, ack=y+1，双方状态变为ESTABLISHED\n\n"
            "为什么是三次：\n"
            "1. 双方都需要确认对方的收发能力\n"
            "2. 如果只有两次握手，服务端无法确认客户端收到了自己的ACK\n"
            "3. 遇到网络中滞留的历史SYN请求，服务端会建立无效连接白白浪费资源\n"
            "4. 为什么不是四次：服务器把SYN和ACK合并成一个包发送了"
        ),
    },
    {
        "stem": "HashMap的底层实现原理是什么？哈希冲突怎么解决？什么时候会扩容？负载因子是多少？",
        "category": "数据结构",
        "difficulty": 3,
        "reference_answer": (
            "Java HashMap底层结构：数组 + 链表 + 红黑树\n"
            "1. 数组（bucket数组）是主体，通过key的hashCode定位数组下标\n"
            "2. 哈希冲突时用链表法（拉链法），新元素挂在链表后面\n"
            "3. 链表长度超过8且数组长度>=64时，链表转红黑树\n"
            "4. 红黑树节点减少到6时，退化为链表\n\n"
            "扩容机制：\n"
            "1. 默认负载因子0.75，当元素数量超过 容量x0.75 时扩容\n"
            "2. 扩容是翻倍（如16变32）\n"
            "3. 扩容时需要重新计算每个元素的位置\n\n"
            "注意：链表法和开放寻址法是两种不同的冲突解决方案，Java的HashMap用的是链表法。"
        ),
    },
    {
        "stem": "红黑树有什么特点？和普通二叉搜索树、AVL树相比有什么优势？",
        "category": "数据结构",
        "difficulty": 4,
        "reference_answer": (
            "红黑树特点（5条规则）：\n"
            "1. 节点要么是红色要么是黑色\n"
            "2. 根节点是黑色\n"
            "3. 叶子节点（NIL）是黑色\n"
            "4. 红色节点的两个子节点都是黑色（不能有两个连续红色）\n"
            "5. 从任一节点到其每个叶子节点的路径上包含相同数目的黑色节点\n\n"
            "对比：\n"
            "1. 普通二叉搜索树最坏情况退化为链表（O(n)）\n"
            "2. AVL树严格平衡（左右子树高度差不超过1），查找最快但旋转频繁，修改代价高\n"
            "3. 红黑树近似平衡（最长路径不超过最短路径的两倍），插入删除最多3次旋转+变色，综合性能更优\n\n"
            "适用场景：红黑树适合频繁增删的场景（如HashMap、TreeMap），AVL适合查询多修改少的场景。"
        ),
    },
    {
        "stem": "你知道哪些设计模式？挑你最熟悉的两三个说说它们的使用场景和实现思路。",
        "category": "设计模式",
        "difficulty": 3,
        "reference_answer": (
            "策略模式：将每一种算法/行为封装为独立的类，比起if-else/switch更加灵活可扩展。应用场景如支付系统中根据用户选择切换支付宝、微信等不同支付策略。\n\n"
            "观察者模式：当某个对象状态变化时，自动通知所有依赖它的对象。应用场景如Vue的响应式系统，数据变化自动通知视图更新；DOM事件监听也是观察者模式。\n\n"
            "装饰器模式：动态地给对象添加功能，比继承更灵活。Python的@staticmethod、@classmethod就是装饰器语法糖；Java的IO流体系（BufferedInputStream包装FileInputStream）也是装饰器模式。"
        ),
    },
    {
        "stem": "CSS盒模型是什么？标准盒模型（content-box）和IE盒模型（border-box）有什么区别？如何统一？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "CSS盒模型描述了元素在页面中占据的空间，包含content、padding、border、margin四层。\n\n"
            "标准盒模型（content-box）：width只包含内容区域，加上padding和border后整体宽度会变大。\n"
            "IE盒模型（border-box）：width包含content + padding + border，整体宽度固定不变。\n\n"
            "统一方法：\n"
            "*, *::before, *::after { box-sizing: border-box; }\n\n"
            "实际开发中99%的情况都用border-box，因为它更符合直觉，布局更容易控制。"
        ),
    },
    {
        "stem": "Vue 2和Vue 3的响应式原理有什么区别？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "Vue 2：使用Object.defineProperty，遍历data中的每个属性，通过getter收集依赖，setter触发更新。\n"
            "缺点：\n"
            "1. 无法检测新增/删除属性（需要$set、$delete）\n"
            "2. 数组需要特殊处理（重写了push、pop等7个方法）\n"
            "3. 需要预先遍历所有属性，性能开销\n\n"
            "Vue 3：使用Proxy，代理整个对象而不是每个属性。\n"
            "优势：\n"
            "1. 能检测新增/删除属性\n"
            "2. 能代理数组\n"
            "3. 懒代理（只有访问到某个属性时才递归代理），性能更好\n"
            "4. 支持Map、Set等更多数据类型"
        ),
    },
    {
        "stem": "Vue中父子组件之间怎么通信？兄弟组件之间呢？还有哪些其他通信方式？",
        "category": "前端",
        "difficulty": 2,
        "reference_answer": (
            "父子组件通信：\n"
            "1. 父传子：props\n"
            "2. 子传父：$emit事件\n\n"
            "兄弟组件通信：\n"
            "1. 状态提升（将共享状态提升到共同的父组件）\n"
            "2. 全局状态管理（Vuex/Pinia）\n\n"
            "其他通信方式：\n"
            "1. provide/inject：祖先组件直接注入数据给任意后代组件，适合深层嵌套\n"
            "2. Event Bus（Vue 2常见）：全局事件总线，Vue 3官方不太推荐\n"
            "3. $refs：父组件直接访问子组件实例\n"
            "4. Vuex/Pinia：适合跨多层级的组件共享状态"
        ),
    },
    {
        "stem": "HTTPS和HTTP有什么区别？TLS握手过程是怎样的？",
        "category": "计算机网络",
        "difficulty": 3,
        "reference_answer": (
            "HTTPS vs HTTP区别：\n"
            "1. HTTPS比HTTP多一层TLS加密\n"
            "2. HTTP端口80，HTTPS端口443\n"
            "3. HTTPS需要CA颁发的证书\n"
            "4. HTTPS可以防止中间人攻击和数据篡改\n\n"
            "TLS握手过程（RSA方式）：\n"
            "1. ClientHello：客户端发送支持的TLS版本、加密套件列表、客户端随机数\n"
            "2. ServerHello：服务端选择加密套件，发送服务端随机数和证书\n"
            "3. 客户端验证证书，生成预主密钥（Pre-Master Secret），用服务端公钥加密后发送\n"
            "4. 双方各自用三个随机数算出会话密钥\n"
            "5. 之后的通信使用对称加密的会话密钥加密\n\n"
            "ECDHE方式下，双方通过KeyShare交换临时公钥，实现前向安全性。"
        ),
    },
    {
        "stem": "ConcurrentHashMap是如何实现线程安全的？JDK 1.7和1.8有什么区别？",
        "category": "数据结构",
        "difficulty": 4,
        "reference_answer": (
            "JDK 1.7：使用Segment分段锁，默认16个Segment。每个Segment独立加锁，不同Segment之间的操作互不影响，支持高并发。\n\n"
            "JDK 1.8：改为CAS + synchronized。\n"
            "1. 对数组元素的首次写入使用CAS无锁操作\n"
            "2. 冲突时（链表/红黑树节点操作）使用synchronized锁住头节点\n"
            "3. 锁的粒度更细（锁单个桶而不是整个段）\n"
            "4. 底层结构也改为数组+链表+红黑树\n\n"
            "1.8的方案并发度更高，实现也更简洁。"
        ),
    },
    {
        "stem": "Two Sum问题：给定一个数组nums和目标值target，找出数组中两个数使得它们的和等于target，返回下标。你会用几种方法？最优解是什么？",
        "category": "数据结构",
        "difficulty": 2,
        "reference_answer": (
            "方法一：暴力双重循环，时间O(n^2)，空间O(1)\n\n"
            "方法二（最优）：一次遍历+HashMap\n"
            "遍历数组，对每个数先检查target-nums[i]是否在map中，如果在就返回；不在就把当前数和下标存入map。\n"
            "时间复杂度O(n)，空间复杂度O(n)\n\n"
            "方法三：排序+双指针，时间O(nlogn)，空间O(1)，但会丢失原始下标信息\n\n"
            "面试中首选方法二，是最优解。"
        ),
    },
    {
        "stem": "什么是TCP四次挥手？为什么建立连接是三次，断开连接是四次？",
        "category": "计算机网络",
        "difficulty": 3,
        "reference_answer": (
            "四次挥手过程：\n"
            "1. 客户端发送FIN=1，进入FIN_WAIT_1状态\n"
            "2. 服务端回复ACK，进入CLOSE_WAIT状态；客户端收到后进入FIN_WAIT_2状态\n"
            "3. 服务端发送FIN=1，进入LAST_ACK状态\n"
            "4. 客户端回复ACK，进入TIME_WAIT状态（等待2MSL后关闭）；服务端收到后关闭\n\n"
            "为什么是四次：\n"
            "TCP是全双工通信，发送FIN只表示不再发送数据，但还能接收数据。\n"
            "服务端收到FIN时可能还有数据要发送，所以ACK和FIN要分开发。\n"
            "建立连接时服务端可以把SYN和ACK合并，因为此时没有数据要传。"
        ),
    },
    {
        "stem": "JavaScript中的this指向规则有哪些？如何改变this的指向？call、apply、bind有什么区别？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "this指向规则（按优先级）：\n"
            "1. new绑定：new Foo()，this指向新创建的对象\n"
            "2. 显式绑定：call/apply/bind，this指向指定的对象\n"
            "3. 隐式绑定：obj.fn()，this指向obj\n"
            "4. 默认绑定：独立函数调用，非严格模式this指向window，严格模式undefined\n\n"
            "call/apply/bind区别：\n"
            "1. call(thisArg, arg1, arg2)：立即执行，参数逐个传\n"
            "2. apply(thisArg, [args])：立即执行，参数数组传\n"
            "3. bind(thisArg)：返回新函数，不立即执行\n\n"
            "箭头函数没有自己的this，继承外层作用域的this。"
        ),
    },
    {
        "stem": "HTTP缓存机制是什么？强缓存和协商缓存有什么区别？相关头部字段有哪些？",
        "category": "计算机网络",
        "difficulty": 3,
        "reference_answer": (
            "HTTP缓存分为强缓存和协商缓存。\n\n"
            "强缓存（不发请求，直接用本地缓存）：\n"
            "1. Expires：绝对过期时间（HTTP/1.0）\n"
            "2. Cache-Control：相对时间，优先级高于Expires（HTTP/1.1）\n"
            "   - max-age=3600：缓存有效3600秒\n"
            "   - no-cache：跳过强缓存，走协商缓存\n"
            "   - no-store：完全不缓存\n\n"
            "协商缓存（发请求，服务器决定是否用缓存）：\n"
            "1. Last-Modified / If-Modified-Since：基于文件修改时间\n"
            "2. ETag / If-None-Match：基于内容哈希值，优先级更高\n\n"
            "命中协商缓存返回304 Not Modified。"
        ),
    },
    {
        "stem": "什么是跨域？为什么会有跨域问题？常见的解决方案有哪些？",
        "category": "计算机网络",
        "difficulty": 3,
        "reference_answer": (
            "跨域是浏览器的同源策略限制：协议、域名、端口任一不同即为跨域。\n\n"
            "同源策略是为了安全，防止恶意网站窃取用户数据。\n\n"
            "常见解决方案：\n"
            "1. CORS（最主流）：服务端设置Access-Control-Allow-Origin等响应头\n"
            "2. 代理服务器：开发环境用webpack/vite的devServer.proxy，生产环境用Nginx反向代理\n"
            "3. JSONP：利用script标签不受同源限制，只支持GET请求\n"
            "4. WebSocket：不受同源策略限制\n"
            "5. postMessage：用于iframe跨域通信"
        ),
    },
    {
        "stem": "Vue的虚拟DOM和Diff算法是怎么工作的？key的作用是什么？",
        "category": "前端",
        "difficulty": 3,
        "reference_answer": (
            "虚拟DOM：用JavaScript对象描述真实DOM结构。当数据变化时，先在虚拟DOM上计算出差异（Diff），再只更新变化的部分到真实DOM，减少DOM操作次数。\n\n"
            "Diff算法（同层比较）：\n"
            "1. 只比较同层级节点，不跨层级比较\n"
            "2. tag不同直接删除重建\n"
            "3. tag相同比较属性和子节点\n"
            "4. 列表比较使用双端比较+最长递增子序列算法\n\n"
            "key的作用：\n"
            "1. 帮助Vue识别哪些节点是复用的、哪些是新增/删除的\n"
            "2. 用index作为key的问题：列表增删时key会变化，导致复用错误\n"
            "3. 应该用唯一标识（如id）作为key"
        ),
    },
]

def main():
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for q_data in questions:
            existing = db.query(Question).filter(Question.stem == q_data["stem"]).first()
            if existing:
                print(f"SKIP (duplicate): {q_data['stem'][:50]}...")
                skipped += 1
                continue
            q = Question(**q_data)
            db.add(q)
            db.flush()
            sync_question_chunks(db, q)
            inserted += 1
            print(f"INSERTED: {q_data['stem'][:50]}...")
        db.commit()
        total = db.query(Question).count()
        print(f"\nDone! Inserted: {inserted}, Skipped: {skipped}, Total in DB: {total}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
