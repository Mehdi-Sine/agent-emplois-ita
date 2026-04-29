select s.slug, count(*) as offers_count
from offers o
join sources s on s.id = o.source_id
where s.slug in ('acta','armeflhor','ceva','inov3pt','cnpf')
group by s.slug
order by s.slug;

select
  s.slug,
  o.id,
  o.title,
  o.is_active,
  o.archived_at,
  o.source_url,
  o.updated_at
from offers o
join sources s on s.id = o.source_id
where s.slug in ('acta','armeflhor','ceva','inov3pt','cnpf')
order by s.slug, o.updated_at desc;
