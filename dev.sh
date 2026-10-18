#!/usr/bin/env bash
set -e

container_id_pg=ci_postgres
pg_img="postgres:18"
container_id_md=ci_mariadb
md_img="mariadb:12"

case "$1" in
	"pull")
		docker pull "$pg_img"
		docker pull "$md_img"
		;;
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
			"$pg_img"
		docker run \
			-e MARIADB_PASSWORD=secret \
			-e MARIADB_USER=dbuser \
			-e MARIADB_DATABASE=test_db \
			-e MARIADB_RANDOM_ROOT_PASSWORD=1 \
			-p 127.0.0.1:30001:3306/tcp \
			--health-cmd='healthcheck.sh --connect --innodb_initialized' \
			--health-interval 1s \
			--health-retries 30 \
			--health-start-period 1s \
			--health-timeout 1s \
			--name="$container_id_md" \
			-d \
			"$md_img"

		while [ "$(docker inspect -f \{\{.State.Health.Status\}\} $container_id_pg)" != "healthy" ]; do
			echo "waiting for container $container_id_pg start..."
			sleep 2
		done

		while [ "$(docker inspect -f \{\{.State.Health.Status\}\} $container_id_md)" != "healthy" ]; do
			echo "waiting for container $container_id_md start..."
			sleep 2
		done
		;;
esac
