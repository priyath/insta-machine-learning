drop table if exists ACCOUNT_INFO;
    create table ACCOUNT_INFO (
    username text primary key,
    q1_status text not null,
    q2_status text not null,
    q3_status text not null,
    result text
);