create database candles;

create table candles.usd_jpy_m15(
  time      datetime primary key,
  open      float,
  high      float,
  low       float,
  close     float,
  volume    int,
  complete  varchar(5)
);
