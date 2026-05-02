@echo off
echo ========================================
echo   Prometheus + ELK 测试环境启动
echo ========================================
echo.
echo 启动的服务:
echo   - Prometheus:   http://localhost:9090
echo   - Node Exporter: http://localhost:9100
echo   - Alertmanager: http://localhost:9093
echo   - Grafana:      http://localhost:3000
echo   - Elasticsearch: http://localhost:9200
echo   - Kibana:       http://localhost:5601
echo   - Logstash:     http://localhost:9600
echo.
echo ========================================
docker compose up -d
echo.
echo 启动完成！访问上述地址验证服务
pause