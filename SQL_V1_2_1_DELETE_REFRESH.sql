begin;

with targets as (
  select o.id
  from offers o
  join sources s on s.id = o.source_id
  where s.slug in ('acta','armeflhor','ceva','inov3pt','cnpf')
)
delete from offer_snapshots
where offer_id in (select id from targets);

with targets as (
  select o.id
  from offers o
  join sources s on s.id = o.source_id
  where s.slug in ('acta','armeflhor','ceva','inov3pt','cnpf')
)
delete from offers
where id in (select id from targets);

commit;
