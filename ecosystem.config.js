module.exports = {
  apps: [
    {
      name: 'dragon-market',
      script: '/home/ubuntu/dragon-radar/venv/bin/uvicorn',
      args: 'main:app --host 127.0.0.1 --port 8001',
      cwd: '/home/ubuntu/dragon-radar/services/market',
      interpreter: 'none',
      env: {
        REDIS_URL: 'redis://127.0.0.1:6379',
      },
      autorestart: true,
      watch: false,
    },
    {
      name: 'dragon-strategy',
      script: '/home/ubuntu/dragon-radar/venv/bin/uvicorn',
      args: 'main:app --host 127.0.0.1 --port 8002',
      cwd: '/home/ubuntu/dragon-radar/services/strategy',
      interpreter: 'none',
      env: {
        REDIS_URL: 'redis://127.0.0.1:6379',
      },
      autorestart: true,
      watch: false,
    },
    {
      name: 'dragon-gateway',
      script: '/home/ubuntu/dragon-radar/gateway/src/index.js',
      cwd: '/home/ubuntu/dragon-radar/gateway',
      env: {
        NODE_ENV: 'production',
        PORT: '3000',
        REDIS_URL: 'redis://127.0.0.1:6379',
        MARKET_SERVICE_URL: 'http://127.0.0.1:8001',
        STRATEGY_SERVICE_URL: 'http://127.0.0.1:8002',
        AI_SERVICE_URL: 'http://127.0.0.1:8003',
      },
      autorestart: true,
      watch: false,
    },
  ],
};
