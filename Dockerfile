FROM postgres:latest
RUN apt-get update
RUN apt-get install -y postgresql-contrib
COPY database/init.sql /docker-entrypoint-initdb.d/
COPY database/pg_hba.conf /docker-entrypoint-initdb.d/
COPY database/setup.sh /docker-entrypoint-initdb.d/
EXPOSE 5432
CMD ["postgres"]
