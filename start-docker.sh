#!/bin/bash
# 简历解析工具 - Docker 启动脚本

set -e

echo "📦 简历解析工具 - Docker 容器化部署"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安装"
    exit 1
fi

cd "$(dirname "$0")"

case "${1:-up}" in
    up)
        echo "🚀 启动服务..."
        docker-compose up -d --build
        echo ""
        echo "✅ 服务已启动！"
        echo "   访问地址: http://localhost:8000"
        echo ""
        echo "📋 常用命令:"
        echo "   查看日志: docker-compose logs -f"
        echo "   停止服务: docker-compose down"
        echo "   重启服务: docker-compose restart"
        ;;
    down)
        echo "🛑 停止服务..."
        docker-compose down
        ;;
    restart)
        echo "🔄 重启服务..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    rebuild)
        echo "🔨 重新构建镜像..."
        docker-compose up -d --build --force-recreate
        ;;
    *)
        echo "用法: $0 {up|down|restart|logs|status|rebuild}"
        exit 1
        ;;
esac
