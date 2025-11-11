#!/usr/bin/env bash

container_id=ci_postgres
case "$1" in
    "stop")
        docker stop "$container_id"
        docker rm "$container_id"
        ;;
    *)
        docker run \
            -e POSTGRES_PASSWORD=secret \
            -e POSTGRES_USER=dbuser \
            -e POSTGRES_DB=test_db \
            -p 127.0.0.1:30000:5432/tcp \
            --health-cmd='PGPASSWORD=$POSTGRES_PASSWORD psql \
            --user=$POSTGRES_USER --dbname=$POSTGRES_DB \
            --host=127.0.0.1 --quiet --no-align --tuples-only \
            -1 --command="SELECT 1"' \
            --health-interval 1s \
            --health-retries 30 \
            --health-start-period 1s \
            --health-timeout 1s \
            --name="$container_id" \
            -d \
            timescale/timescaledb-ha:pg18-all
        while [ "$(docker inspect -f \{\{.State.Health.Status\}\} $container_id)" != "healthy" ]; do
            echo "waiting for container start..."
            sleep 2
        done
        ;;
esac
