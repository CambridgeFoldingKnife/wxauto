# 健衡学园 · 公众号发布配置
#
# ★ default_theme 必须保持 `jianheng`（公司品牌主题，随包提供）。
#   ⚠️ 不要写成 jianhengxueyuan / jianheng-xueyuan / jianheng_xueyuan ——
#      主题文件名就是 jianheng.css，写错会直接报：
#      Error: Missing theme CSS for "xxx": .../themes/xxx.css
#      注意区分：`jianheng-xueyuan` 是【账号 alias】，不是主题名。
default_theme: jianheng
default_publish_method: api
default_author: 健衡学园
need_open_comment: 1
only_fans_can_comment: 0

# ── 多账号（以后需要发布到「健衡康复资讯」时再启用） ──
# accounts:
#   - name: 健衡学园
#     alias: jianheng-xueyuan
#     default: true
#   - name: 健衡康复资讯
#     alias: jianheng-kangfu