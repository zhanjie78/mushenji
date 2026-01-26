PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE canon_sources (
  source_id      INTEGER PRIMARY KEY,
  source_type    TEXT NOT NULL CHECK (source_type IN ('novel_chapter','web_article','other')),
  source_title   TEXT NOT NULL,
  source_url     TEXT,
  notes          TEXT
);
INSERT INTO canon_sources VALUES(1,'novel_chapter','《牧神记》：延康国三大教派（道门/大雷音寺/天魔教）相关段落','https://www.piaotia.com/html/8/8755/5785193.html','网页转录章节；用于校验“三大教派”表述');
INSERT INTO canon_sources VALUES(2,'novel_chapter','《牧神记》：道门、天魔教与大雷音寺“三大圣地”表述','https://www.qidian.com/chapter/1009704712/383781996/','起点章节页面');
INSERT INTO canon_sources VALUES(3,'novel_chapter','《牧神记》：大雷音寺主持自称“如来”','https://uukanshu.cc/book/866/376466.html','章节转录；用于“如来”称谓');
INSERT INTO canon_sources VALUES(4,'novel_chapter','《牧神记》：小雷音寺创立与搬迁到大墟（小如来、叛出大雷音寺）','https://www.qidian.com/chapter/1009704712/378794326/','起点章节页面（第六十三章）');
INSERT INTO canon_sources VALUES(5,'novel_chapter','《牧神记》：小雷音寺在大墟的地位（大墟唯一圣地、妖和尚众多）','https://mtiyu.bookresource.qq.com/chapter/1009704712/397664132/','QQ bookresource 章节转录（第四百七十八章）');
INSERT INTO canon_sources VALUES(6,'novel_chapter','《牧神记》：难陀寺与孙难陀（灵宝不动禅功）','https://tw.hjwzw.com/Book/Read/36278%2C12689557','章节转录（第二百一十二章）');
INSERT INTO canon_sources VALUES(7,'web_article','《牧神记》“七大神藏”破壁与境界名称概述','https://www.zhihu.com/question/380047941/answer/2751811394','用于校验境界名称顺序');
INSERT INTO canon_sources VALUES(8,'web_article','《牧神记》“七大神藏”表述（引用原文式概述）','https://www.qimao.com/shuku/1784908/','用于校验“七大神藏”列表');
CREATE TABLE canon_links (
  link_id        INTEGER PRIMARY KEY,
  entity_type    TEXT NOT NULL CHECK (entity_type IN ('world_area','cultivation_realm','organization','org_relation','org_method','org_doctrine','world_setting','faction')),
  entity_id      INTEGER NOT NULL,
  source_id      INTEGER NOT NULL REFERENCES canon_sources(source_id) ON DELETE CASCADE,
  claim_summary  TEXT NOT NULL
);
INSERT INTO canon_links VALUES(1,'cultivation_realm',1,7,'七大神藏境界列表/破壁概述');
INSERT INTO canon_links VALUES(2,'cultivation_realm',1,8,'七大神藏列表（灵胎到神桥）');
INSERT INTO canon_links VALUES(3,'organization',1,1,'延康国三大教派：道门（正道第一）');
INSERT INTO canon_links VALUES(4,'organization',2,1,'延康国三大教派：大雷音寺（佛门第一）');
INSERT INTO canon_links VALUES(5,'organization',3,1,'延康国三大教派：天魔教（魔道第一）');
INSERT INTO canon_links VALUES(6,'organization',1,2,'道门/天魔教/大雷音寺“三大圣地”并列表述');
INSERT INTO canon_links VALUES(7,'organization',2,3,'大雷音寺主持自称“如来”');
INSERT INTO canon_links VALUES(8,'organization',4,4,'小雷音寺创立背景：小如来叛出大雷音寺，迁入大墟');
INSERT INTO canon_links VALUES(9,'organization',4,5,'小雷音寺在大墟：唯一圣地、妖和尚众多');
INSERT INTO canon_links VALUES(10,'organization',5,6,'难陀寺、孙难陀、灵宝不动禅功线索');
INSERT INTO canon_links VALUES(11,'org_relation',1,4,'小雷音寺与大雷音寺的“叛出/创立”关系');
CREATE TABLE world_areas (
  area_id        INTEGER PRIMARY KEY,
  id             INTEGER UNIQUE,
  code           TEXT UNIQUE,
  name_cn        TEXT NOT NULL,
  name_pinyin    TEXT,
  area_type      TEXT NOT NULL DEFAULT 'unknown' CHECK (area_type IN ('world','continent','country','region','city','site','unknown')),
  parent_area_id INTEGER REFERENCES world_areas(area_id) ON DELETE SET NULL,
  description    TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1)),
  tier           INTEGER
);
INSERT INTO world_areas VALUES(1,1,'WORLD','牧神记世界','MuShenJi','world',NULL,'《牧神记》主世界，用于统一挂载区域/国家/地点。',1,NULL);
INSERT INTO world_areas VALUES(2,2,'YANKANG','延康国','YanKang','country',1,'延康国（国家/政权）。',1,NULL);
INSERT INTO world_areas VALUES(3,3,'DAXU','大墟','DaXu','region',1,'大墟（特殊区域）。',1,NULL);
INSERT INTO world_areas VALUES(4,4,'JINGCHENG','京城','JingCheng','city',2,'延康国京城（都城/京师）。',1,NULL);
INSERT INTO world_areas VALUES(5,5,'UNKNOWN','未知','Unknown','unknown',1,'用于暂未在本次整理中锁定的地理归属。',0,NULL);
INSERT INTO world_areas VALUES(6,6,'KAIHUANG','开皇',NULL,'unknown',NULL,'上古强盛的人族国度/时代节点；其“三大圣地”在叙事与设定中反复被引用。',1,2);
INSERT INTO world_areas VALUES(7,7,'XITU','西土',NULL,'unknown',NULL,'佛门势力活动的关键地域之一；须弥山体系在此叙事权重很高。',1,2);
INSERT INTO world_areas VALUES(8,8,'XUMISHAN','须弥山',NULL,'unknown',NULL,'大雷音寺所在圣地（佛门核心地标）。',1,2);
INSERT INTO world_areas VALUES(9,9,'XIAOXUMISHAN','小须弥山',NULL,'unknown',NULL,'小雷音寺所在；格局与许多布置照搬大雷音寺，但底蕴较浅。',1,2);
INSERT INTO world_areas VALUES(10,10,'JIANCHI','剑池',NULL,'unknown',NULL,'道门圣地（开皇三大圣地之一，道统象征地标）。',1,2);
INSERT INTO world_areas VALUES(11,11,'WUYAOXIANG','无忧乡',NULL,'unknown',NULL,'开皇三大圣地之一；可作为中后期扩展舞台/剧情钥匙。',1,2);
INSERT INTO world_areas VALUES(12,12,'XIAOYUJING','小玉京',NULL,'unknown',NULL,'与道门求道者、天盟会盟线强关联的“聚点/据点/洞天”概念地标。',1,2);
CREATE TABLE world_settings (
  setting_id     INTEGER PRIMARY KEY,
  scope_area_id  INTEGER REFERENCES world_areas(area_id) ON DELETE SET NULL,
  setting_key    TEXT NOT NULL,
  setting_value  TEXT NOT NULL,
  notes          TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1))
);
INSERT INTO world_settings VALUES(1,2,'three_major_sects','道门 / 大雷音寺 / 天魔教','延康常被概括为“三大教派”。',1);
INSERT INTO world_settings VALUES(2,3,'holy_land_status','小雷音寺被描述为“大墟唯一圣地”','用于大墟区域的势力格局。',1);
CREATE TABLE cultivation_systems (
  system_code    TEXT PRIMARY KEY,
  name_cn        TEXT NOT NULL,
  description    TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1))
);
INSERT INTO cultivation_systems VALUES('SHENZANG','七大神藏体系','人体七大宝库（灵胎、五曜、六合、七星、天人、生死、神桥）及破壁开藏的修炼体系。',1);
CREATE TABLE cultivation_realms (
  realm_id       INTEGER PRIMARY KEY,
  system_code    TEXT NOT NULL REFERENCES cultivation_systems(system_code) ON DELETE CASCADE,
  seq            INTEGER NOT NULL,
  name_cn        TEXT NOT NULL,
  description    TEXT,
  notes          TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1)),
  UNIQUE(system_code, seq),
  UNIQUE(system_code, name_cn)
);
INSERT INTO cultivation_realms VALUES(1,'SHENZANG',1,'灵胎','七大神藏第一藏。','破开灵胎壁开始真正修炼。',1);
INSERT INTO cultivation_realms VALUES(2,'SHENZANG',2,'五曜','以灵胎为中心衍生五曜。',NULL,1);
INSERT INTO cultivation_realms VALUES(3,'SHENZANG',3,'六合','灵台衍生六合。',NULL,1);
INSERT INTO cultivation_realms VALUES(4,'SHENZANG',4,'七星','六合成就后再生日月，合为七星。',NULL,1);
INSERT INTO cultivation_realms VALUES(5,'SHENZANG',5,'天人','元神强大，衍生成天人。',NULL,1);
INSERT INTO cultivation_realms VALUES(6,'SHENZANG',6,'生死','元神连通生死。',NULL,1);
INSERT INTO cultivation_realms VALUES(7,'SHENZANG',7,'神桥','踏神桥可至天宫等更高层次。',NULL,1);
CREATE TABLE factions (
  faction_id     INTEGER PRIMARY KEY,
  code           TEXT UNIQUE,
  name_cn        TEXT NOT NULL UNIQUE,
  faction_type   TEXT,
  alignment      TEXT,
  description    TEXT,
  home_area_id   INTEGER REFERENCES world_areas(area_id) ON DELETE SET NULL,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1))
);
INSERT INTO factions VALUES(1,NULL,'延康三大教派','sect_bloc',NULL,'延康国常被概括为三大教派并立：道门（正道第一）、大雷音寺（佛门第一）、天魔教（魔道第一）。',2,1);
INSERT INTO factions VALUES(2,NULL,'佛门','religion_bloc',NULL,'以寺院体系为主的宗派阵营（用于组织分类）。',NULL,0);
INSERT INTO factions VALUES(3,NULL,'正道','sect_bloc',NULL,'正道宗派阵营（用于组织分类）。',NULL,0);
INSERT INTO factions VALUES(4,NULL,'魔道','sect_bloc',NULL,'魔道宗派阵营（用于组织分类）。',NULL,0);
INSERT INTO factions VALUES(5,'FOMEN','佛门势力',NULL,'traditional','以须弥山大雷音寺体系为核心的佛门传统力量，兼具诸天模型与寺院组织形态。',NULL,1);
INSERT INTO factions VALUES(6,'DAOMEN','道门势力',NULL,'traditional','以道主/道子与剑池道统为核心的道门传统力量，讲求验证与传承秩序。',NULL,1);
CREATE TABLE faction_members (
  faction_id     INTEGER NOT NULL REFERENCES factions(faction_id) ON DELETE CASCADE,
  org_id         INTEGER NOT NULL,
  role_in_faction TEXT,
  PRIMARY KEY (faction_id, org_id)
);
INSERT INTO faction_members VALUES(1,1,'正道第一');
INSERT INTO faction_members VALUES(1,2,'佛门第一');
INSERT INTO faction_members VALUES(1,3,'魔道第一');
CREATE TABLE organizations (
  org_id         INTEGER PRIMARY KEY,
  name_cn        TEXT NOT NULL,
  name_pinyin    TEXT,
  org_kind       TEXT NOT NULL CHECK (org_kind IN ('sect','temple','academy','state','clan','holy_land','other')),
  camp_tag       TEXT,
  home_area_id   INTEGER REFERENCES world_areas(area_id) ON DELETE SET NULL,
  leader_title   TEXT,
  founder_name   TEXT,
  description    TEXT,
  notes          TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1))
);
INSERT INTO organizations VALUES(1,'道门','DaoMen','sect','正道',5,'道主',NULL,'延康国三大教派之一，常被称为“正道第一”。','本次先落入“未知”地理；后续你可以在确定其山门/圣地后再改 home_area_id。',1);
INSERT INTO organizations VALUES(2,'大雷音寺','DaLeiYinSi','temple','佛门',5,'如来',NULL,'延康国三大教派之一，常被称为“佛门第一”。其主持自称“如来”。','如来称谓见章节转录。',1);
INSERT INTO organizations VALUES(3,'天魔教','TianMoJiao','sect','魔道',5,'教主',NULL,'延康国三大教派之一，常被称为“魔道第一”。','教主称谓为通用称谓；如需更精确可扩展组织职位表。',1);
INSERT INTO organizations VALUES(4,'小雷音寺','XiaoLeiYinSi','temple','佛门',3,'小如来','小如来','由小如来创立，后迁入大墟。小雷音寺在大墟被描述为“唯一圣地”，妖和尚众多。','小如来出身与搬迁缘由见第六十三章；大墟地位见第四百七十八章。',1);
INSERT INTO organizations VALUES(5,'难陀寺','NanTuoSi','temple','佛门',2,'住持',NULL,'佛门寺院之一，与孙难陀相关。','当前仅落库“寺院 + 人名 + 功法线索”，后续可补充其所在更精确地点与隶属关系（若原著有明确表述）。',1);
INSERT INTO organizations VALUES(6,'太学院','TaiXueYuan','academy','学院',2,'祭酒/博士',NULL,'延康的重要学府/修行教育体系节点。','用于承载“堵门”等宗派交流事件（如后续要做事件表）。',1);
CREATE TABLE org_aliases (
  org_id         INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  alias          TEXT NOT NULL,
  alias_type     TEXT NOT NULL CHECK (alias_type IN ('short','nickname','alt_name','translit')),
  PRIMARY KEY (org_id, alias)
);
INSERT INTO org_aliases VALUES(2,'雷音寺','short');
CREATE TABLE org_doctrines (
  doctrine_id    INTEGER PRIMARY KEY,
  org_id         INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  doctrine_key   TEXT NOT NULL,
  doctrine_value TEXT NOT NULL,
  notes          TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1)),
  UNIQUE(org_id, doctrine_key)
);
CREATE TABLE org_methods (
  method_id      INTEGER PRIMARY KEY,
  org_id         INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  method_name_cn TEXT NOT NULL,
  method_type    TEXT NOT NULL CHECK (method_type IN ('core_art','combat_art','mantra','ritual','technique','other')),
  description    TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1)),
  UNIQUE(org_id, method_name_cn)
);
INSERT INTO org_methods VALUES(1,1,'先天太玄功','core_art','道门功法名（与大育天魔经等并列被提及）。',1);
INSERT INTO org_methods VALUES(2,5,'灵宝不动禅功','core_art','难陀寺相关功法名。',1);
CREATE TABLE org_relations (
  relation_id    INTEGER PRIMARY KEY,
  from_org_id    INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  to_org_id      INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  relation_type  TEXT NOT NULL CHECK (relation_type IN ('split_from','branch_of','rival_of','allied_with','hostile_to','influenced_by','member_of')),
  description    TEXT,
  is_canon       INTEGER NOT NULL DEFAULT 1 CHECK (is_canon IN (0,1))
);
INSERT INTO org_relations VALUES(1,4,2,'split_from','小如来原为大雷音寺弟子/僧人，后叛出创立小雷音寺，自号小如来。',1);
CREATE TABLE world_rules (
  id             INTEGER PRIMARY KEY,
  code           TEXT UNIQUE,
  title_cn       TEXT NOT NULL,
  scope_area_id  INTEGER REFERENCES world_areas(area_id) ON DELETE SET NULL,
  importance     INTEGER NOT NULL DEFAULT 0,
  description    TEXT
);
INSERT INTO world_rules VALUES(1,'RULE_KAIHUANG_THREE_HOLY','开皇三大圣地',6,5,'开皇三大圣地：须弥山大雷音寺、道教剑池、无忧乡。适合作为主线钥匙、资料片入口与阵营冲突焦点。');
INSERT INTO world_rules VALUES(2,'RULE_DALEIYIN_RULAI_DACHENG','大雷音寺心法：如来大乘经',8,5,'大雷音寺的核心心法为“如来大乘经”；可作为佛门修行体系、天宫/诸天模型与副本结构的根。');
INSERT INTO world_rules VALUES(3,'RULE_DALEIYIN_LEIYIN_BASHI','佛门拳法：雷音八式（体系入口之一）',8,4,'雷音八式可作为佛门外显技艺线（招式/拳法/战斗表现）的入口，与“如来大乘经”形成内外两条成长线。');
INSERT INTO world_rules VALUES(4,'RULE_XIAOLEIYIN_ORIGIN','小雷音寺起源：叛出大雷音寺，自立小如来',9,5,'小雷音寺祖师原本拜入佛门、为大雷音寺弟子，后叛出自立并自封“小如来”。');
INSERT INTO world_rules VALUES(5,'RULE_XIAOLEIYIN_COPY_LAYOUT','小雷音寺照搬大雷音寺（几百年寺龄）',9,4,'小雷音寺发展只有几百年，缺底蕴，景观与布置多照搬大雷音寺；但僧众/妖僧数量不弱。');
INSERT INTO world_rules VALUES(6,'RULE_DAOMEN_DOOR_BLOCK','道门堵门三日：验证太学院变法',2,5,'道门以“道子”对太学院士子发起公开验证：若太学院资源更胜却不如道子，则变法叙事受冲击。');
INSERT INTO world_rules VALUES(7,'RULE_DAOMEN_DAOJIAN14','道门镇教剑法：道剑十四篇',10,5,'道门镇教剑法“道剑十四篇”可作为道门战斗体系与传承任务链的主轴。');
INSERT INTO world_rules VALUES(8,'RULE_XIAOYUJING_CONCLAVE','小玉京会盟/求道者聚点',12,4,'小玉京可用作“会盟、论道、定策、结盟”的剧情空间，承接天盟/道门/上苍压制多线交汇。');
CREATE TABLE sects (
  id             INTEGER PRIMARY KEY,
  code           TEXT UNIQUE,
  name_cn        TEXT NOT NULL,
  type           TEXT,
  home_area_id   INTEGER REFERENCES world_areas(area_id) ON DELETE SET NULL,
  description    TEXT
);
INSERT INTO sects VALUES(1,'DALEIYINSI','大雷音寺','traditional',8,'佛门核心宗门之一，须弥山体系中枢；以如来大乘经与诸天模型为根基。');
INSERT INTO sects VALUES(2,'XIAOLEIYINSI','小雷音寺','traditional',9,'由叛出大雷音寺的祖师所立，自封小如来；寺龄较浅、布置多照搬大雷音寺。');
INSERT INTO sects VALUES(3,'DAOMEN_ZONG','道门','traditional',10,'道门道统势力；有道主/道子体系，镇教剑法为道剑十四篇；与太学院变法线存在公开验证冲突。');
INSERT INTO sects VALUES(4,'XIAOYUJING_HUI','小玉京','traditional',12,'与道门求道者与会盟线相关的组织/聚点概念；适合作为“论道、会盟、定策”的玩法枢纽。');
INSERT INTO sects VALUES(5,'WUYAOXIANG_ORG','无忧乡','traditional',11,'开皇三大圣地之一；可作为中后期扩展舞台的“组织/聚落/据点”抽象。');
CREATE TABLE sect_rules (
  id             INTEGER PRIMARY KEY,
  sect_id        INTEGER NOT NULL REFERENCES sects(id) ON DELETE CASCADE,
  rule_key       TEXT NOT NULL,
  rule_value     TEXT NOT NULL,
  description    TEXT,
  UNIQUE(sect_id, rule_key)
);
INSERT INTO sect_rules VALUES(1,1,'STRUCTURE','如来/佛子/长老/僧众','最小组织层级：可映射权限、职位与任务发布。');
INSERT INTO sect_rules VALUES(2,1,'STYLE','佛门/诸天模型/戒律与度化/内外双线','玩法风格标签。');
INSERT INTO sect_rules VALUES(3,1,'HOLY_LAND','须弥山（大雷音寺）','宗门地标/副本入口。');
INSERT INTO sect_rules VALUES(4,1,'CORE_SCRIPTURE','如来大乘经','核心心法（佛门体系主轴）。');
INSERT INTO sect_rules VALUES(5,1,'CORE_TECHNIQUE','雷音八式（外显技艺线）','核心招式线，可拆成8段传承任务。');
INSERT INTO sect_rules VALUES(6,1,'CULTIVATION_SUBMODEL','二十诸天（可映射塔/天层/院）','用于构建佛门“诸天”式关卡与境界分段。');
INSERT INTO sect_rules VALUES(7,1,'EVENT_HOOKS','庙会擂台/论法/度化与救治/诸天塔试炼','事件生成钩子（用于机器人剧情/任务）。');
INSERT INTO sect_rules VALUES(8,1,'RESOURCE_INTERFACE','香火/功德/经卷/佛宝','资源接口（掉落、声望、兑换）。');
INSERT INTO sect_rules VALUES(9,2,'STRUCTURE','小如来/高僧/僧众（含妖僧）','最小组织层级：保留“异类僧众”特色。');
INSERT INTO sect_rules VALUES(10,2,'STYLE','佛门分支/照搬大寺格局/异类成道/强对抗','玩法风格标签。');
INSERT INTO sect_rules VALUES(11,2,'HOLY_LAND','小须弥山（小雷音寺金顶）','宗门地标/副本入口。');
INSERT INTO sect_rules VALUES(12,2,'ORIGIN','原为大雷音寺弟子，叛出后自立并自封小如来','原著起源叙事钉子。');
INSERT INTO sect_rules VALUES(13,2,'CANON_DETAIL','寺龄仅数百年；景观布置多与大雷音寺相似（照搬照抄）','用于世界观一致性与场景生成。');
INSERT INTO sect_rules VALUES(14,2,'CORE_SCRIPTURE','如来大乘经（可有分支/残卷/异类注解）','与大雷音寺同源但可做“分歧版本”玩法。');
INSERT INTO sect_rules VALUES(15,2,'EVENT_HOOKS','金顶斗法/寺内派系之争/与大雷音寺的并立或合流','事件生成钩子。');
INSERT INTO sect_rules VALUES(16,2,'RESOURCE_INTERFACE','妖僧供奉/异类功德/残卷经文','资源接口（对抗与异化路线）。');
INSERT INTO sect_rules VALUES(17,3,'STRUCTURE','道主/道子/长老/道士/外门','道门最小组织层级。');
INSERT INTO sect_rules VALUES(18,3,'STYLE','道统/验证与论道/剑法传承/数算','玩法风格标签。');
INSERT INTO sect_rules VALUES(19,3,'HOLY_LAND','剑池','道门圣地（传承与试炼入口）。');
INSERT INTO sect_rules VALUES(20,3,'CORE_TECHNIQUE','道门镇教剑法：道剑十四篇','镇教体系主轴（可拆14式任务链）。');
INSERT INTO sect_rules VALUES(21,3,'CANON_DETAIL','道主与太学院冲突：以道子堵门三日验证变法与教学体系','原著冲突钉子。');
INSERT INTO sect_rules VALUES(22,3,'EVENT_HOOKS','堵门/论道/剑池试炼/道子挑战','事件生成钩子。');
INSERT INTO sect_rules VALUES(23,3,'RESOURCE_INTERFACE','道剑图谱/符箓/丹器/数算卷宗','资源接口（掉落、研究、兑换）。');
INSERT INTO sect_rules VALUES(24,3,'PRACTICE_KEYWORDS','太极图/阴阳变化/剑意分化','用于技能词条与AI生成描述的一致性。');
INSERT INTO sect_rules VALUES(25,4,'STRUCTURE','求道者议席/道门前辈/访客盟友','不强行套“掌门长老”，用议席/会盟更贴叙事。');
INSERT INTO sect_rules VALUES(26,4,'STYLE','会盟/论道/隐世据点','玩法风格标签。');
INSERT INTO sect_rules VALUES(27,4,'HOLY_LAND','小玉京','会盟地标。');
INSERT INTO sect_rules VALUES(28,4,'EVENT_HOOKS','会盟定策/引荐/交换情报/对上界压制的策略讨论','事件生成钩子。');
INSERT INTO sect_rules VALUES(29,4,'RESOURCE_INTERFACE','盟约/情报/古卷/路引','资源接口（任务道具与剧情钥匙）。');
INSERT INTO sect_rules VALUES(30,5,'STRUCTURE','乡主/守护者/来客','聚落式组织结构。');
INSERT INTO sect_rules VALUES(31,5,'STYLE','圣地/隐世/扩展舞台入口','玩法风格标签。');
INSERT INTO sect_rules VALUES(32,5,'HOLY_LAND','无忧乡','开皇三大圣地之一。');
INSERT INTO sect_rules VALUES(33,5,'EVENT_HOOKS','圣地开启/旧时代遗留/关键人物线索','事件生成钩子。');
CREATE TABLE sect_factions (
  sect_id        INTEGER NOT NULL REFERENCES sects(id) ON DELETE CASCADE,
  faction_id     INTEGER NOT NULL REFERENCES factions(faction_id) ON DELETE CASCADE,
  weight         INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (sect_id, faction_id)
);
INSERT INTO sect_factions VALUES(1,5,100);
INSERT INTO sect_factions VALUES(2,5,90);
INSERT INTO sect_factions VALUES(3,6,100);
INSERT INTO sect_factions VALUES(4,6,80);
CREATE TABLE system_settings (
  key            TEXT PRIMARY KEY,
  value          TEXT NOT NULL,
  description    TEXT
);
INSERT INTO system_settings VALUES('FOMEN_CORE_SCRIPTURE','如来大乘经','佛门心法主轴；可与主修炼干线并行或作为分支职业体系。');
INSERT INTO system_settings VALUES('FOMEN_SUBMODEL_20HEAVENS','二十诸天','佛门诸天模型（塔/天层/院）用于关卡、境界分段与副本结构。');
INSERT INTO system_settings VALUES('DAOMEN_CORE_SWORD','道剑十四篇','道门镇教剑法主轴；用于剑法传承、试炼、挑战类玩法。');
INSERT INTO system_settings VALUES('KAIHUANG_THREE_HOLY_LANDS','须弥山大雷音寺/道教剑池/无忧乡','开皇三大圣地作为世界扩展与主线钥匙。');
CREATE TRIGGER world_areas_set_id
AFTER INSERT ON world_areas
WHEN NEW.id IS NULL
BEGIN
  UPDATE world_areas SET id = NEW.area_id WHERE area_id = NEW.area_id;
END;
CREATE UNIQUE INDEX idx_world_areas_name_type ON world_areas(name_cn, area_type);
CREATE INDEX idx_world_areas_code ON world_areas(code);
CREATE INDEX idx_world_settings_scope ON world_settings(scope_area_id, setting_key);
CREATE UNIQUE INDEX idx_org_name_kind ON organizations(name_cn, org_kind);
CREATE INDEX idx_org_rel_from_to ON org_relations(from_org_id, to_org_id, relation_type);
COMMIT;