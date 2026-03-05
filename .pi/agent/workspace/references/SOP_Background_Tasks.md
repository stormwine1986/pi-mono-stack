# 后台任务标准操作程序

## 创建后台处理任务

后台任务都是通过 `dkron` 命令创建的，可以通过 `-h` 查看帮助。
- name 设定为任务名称，必须唯一
- owner 设定为当前会话用户ID
- executor 设定为 `background`
- schedule 非周期性任务设定为 `@at <ISO8601>`，必须使用 `date` 命令获取当前时间，来计算触发时间；周期性任务使用 `@every <duration>`或者 cron 表达式
- command 设定为要执行的命令

命令样例

```bash
# 非周期性任务
dkron job create --name "xxxxx" --owner "<user_id>" --schedule "@at <ISO8601>" --command "<command>" --executor background
# 周期性任务
dkron job create --name "xxxxx" --owner "<user_id>" --schedule "@every <duration>" --command "<command>" --executor background
```

## 创建提醒任务

提醒任务都是通过 `dkron` 命令创建的，可以通过 `-h` 查看帮助。
- name 设定为任务名称，必须唯一
- owner 设定为当前会话用户ID
- executor 设定为 `reminder`
- schedule 设定为 `@at <ISO8601>`，必须使用 `date` 命令获取当前时间，然后计算出提醒时间，除非用户直接指定时间
- message 设定为提醒内容

命令样例

```bash
# 提醒任务
dkron job create --name "xxxxx" --executor reminder --owner "<user_id>" --schedule "@at 2026-03-05T08:00:00Z" --message "该喝咖啡了"
```