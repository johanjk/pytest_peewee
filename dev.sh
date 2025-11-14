#!/usr/bin/env bash

container_id_pg=ci_postgres
container_id_md=ci_mariadb
case "$1" in
	"stop")
		docker stop "$container_id_pg"
		docker rm "$container_id_pg"
		docker stop "$container_id_md"
		docker rm "$container_id_md"
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
			--name="$container_id_pg" \
			-d \
			timescale/timescaledb-ha:pg18-all
		docker run \
			-e MARIADB_PASSWORD=secret \
			-e MARIADB_USER=dbuser \
			-e MARIADB_DATABASE=test_db \
			-p 127.0.0.1:30001:3306/tcp \
			--health-cmd='healthcheck.sh --connect --innodb_initialized' \
			--health-interval 1s \
			--health-retries 30 \
			--health-start-period 1s \
			--health-timeout 1s \
			--name="$container_id_md" \
			-d \
			mariadb:12

		while [ "$(docker inspect -f \{\{.State.Health.Status\}\} $container_id_pg)" != "healthy" ]; do
			echo "waiting for container start..."
			sleep 2
		done

		while [ "$(docker inspect -f \{\{.State.Health.Status\}\} $container_id_md)" != "healthy" ]; do
			echo "waiting for container start..."
			sleep 2
		done
		;;
esac
