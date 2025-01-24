#!/bin/bash
host="$1"
port="$2"
shift 2
cmd="$@"

until nc -z "$host" "$port"; do
  echo "Waiting for MySQL at $host:$port..."
  sleep 3
done

echo "MySQL is up - executing command"
exec $cmd
