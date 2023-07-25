#!/bin/sh
set -ex

if [ "$NODE_ENV" = "development" ]; then
    export SHORT_STAGE="dev"
elif [ "$NODE_ENV" = "staging" ]; then
    export SHORT_STAGE="stg"
fi

FILE_NAME="ecosystem.config.js"
cat <<EOF > "${FILE_NAME}"
module.exports = {
  apps: [{
    name: 'imsv2-$SHORT_STAGE',
    script: 'yarn',
    args: 'run start:$SHORT_STAGE',
    cwd: "/app",
    interpreter: '/bin/bash',
    time: true,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env_development: {
       NODE_ENV: "development"
    },
    env_staging: {
       NODE_ENV: "staging"
    }
  }]
}
EOF

pm2-runtime start ecosystem.config.js --env "$NODE_ENV"
