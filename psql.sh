#!/bin/bash
set -x
function usage(){
	echo "$0 release_note_id"
	exit 1
	}
ENV='prod'
case "$ENV" in 
	'prod')
		PASSWD=''
		PORT=5411
		UNAME=''
		DBNAME=''
		ENDPOINT=''
		;;
	'dev')
		PASSWD=''
		PORT=5411
		UNAME=''
		DBNAME=''
		ENDPOINT=''
		;;
	*)
		usage
		;;
esac
function uep_user(){
PGPASSWORD="${PASSWD}" psql.exe --host=localhost --port="${PORT}" --username="${UNAME}" --dbname="${DBNAME}" << SQL 
SELECT * FROM public.release_note WHERE id = '${1}';
UPDATE public.release_note SET type = 'OPERATOR' WHERE id = '${1}';
SELECT * FROM public.release_note WHERE id = '${1}';
SQL
}
function main(){
	if [[ $1 == '' ]]; then
		usage
	else
		ssh -f -o ExitOnForwardFailure=yes $ENDPOINT sleep 10
		netstat -ano|grep $PORT
		if [[ $(netstat -ano|grep $PORT|wc -l) > 0 ]]; then
			uep_user $1
			return
		fi
		while [[ $(netstat -ano|grep $PORT|wc -l) == 0 ]]; do
			echo "waiting for sync"
			sleep 3
			if [[ $(netstat -ano|grep $PORT|wc -l) > 0 ]]; then
				uep_user $1
				break
			fi
		done
	fi	
}
main $1
