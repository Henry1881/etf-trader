import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scheduler.task_scheduler import TaskScheduler


def main():
    scheduler = TaskScheduler()

    if len(sys.argv) > 1:
        if sys.argv[1] == "run":
            scheduler.run_once()
        elif sys.argv[1] == "start":
            try:
                scheduler.start()
                while True:
                    pass
            except KeyboardInterrupt:
                scheduler.stop()
        else:
            print("用法: python main.py [run|start]")
            print("  run   - 执行单次报告生成")
            print("  start - 启动定时任务调度器")
            sys.exit(1)
    else:
        print("用法: python main.py [run|start]")
        print("  run   - 执行单次报告生成")
        print("  start - 启动定时任务调度器")
        sys.exit(1)


if __name__ == "__main__":
    main()
