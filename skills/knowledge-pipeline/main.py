import json
import os
import re
import psycopg2
import psycopg2.extras
import sys
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

_PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
_PG_PORT = int(os.environ.get("PG_PORT", "5432"))
_PG_USER = os.environ.get("PG_USER", "GodyChang")
_PG_PASS = os.environ.get("PG_PASSWORD", "")
_PG_DB = os.environ.get("PG_DATABASE", "aims")

# 文本分块策略：每块800字符，块间重叠100字符（保证上下文连续）
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 向量维度：与 embedding model (all-MiniLM-L6-v2) 输出对齐
VECTOR_DIM = 384

# 电商知识库（内置）：跨境电商运营/平台规则/产品开发/广告投放/物流仓储/财务合规
ECOMMERCE_KNOWLEDGE = {
    "cross_border_ops": {
        "name": "跨境电商运营",
        "description": "跨境电商运营策略、平台操作、店铺管理",
        "documents": [
            {
                "title": "亚马逊运营核心指标体系",
                "content": "亚马逊运营核心指标包括：1) BSR(Best Seller Rank)类目排名，反映产品在类目中的竞争力；2) 转化率(Unit Session Percentage)，建议维持在10%以上；3) ACOS(广告销售成本比)，目标25%-35%；4) 利润率，扣除FBA费用、佣金、广告成本后建议保持20%以上；5) 库存周转率，避免断货和滞销；6) 退货率，控制在5%以内；7) IPI库存绩效指标，保持500以上。这些指标需要每日监控，异常时及时调整策略。",
                "tags": ["亚马逊", "运营指标", "BSR", "转化率", "ACOS"],
            },
            {
                "title": "Shopify独立站运营策略",
                "content": "Shopify独立站运营要点：1) 网站设计要专业简洁，加载速度控制在3秒内；2) 产品页面要有高质量图片和详细描述；3) 支付方式要多样化，支持PayPal、信用卡等；4) 物流政策要透明，提供多种配送选项；5) 邮件营销是核心，设置自动化邮件流程；6) 社交媒体引流，Facebook/Instagram/TikTok广告投放；7) SEO优化，提升自然搜索流量；8) 客户评价管理，提升信任度。独立站的核心是品牌建设和私域流量运营。",
                "tags": ["Shopify", "独立站", "品牌建设", "私域流量"],
            },
            {
                "title": "TikTok Shop运营指南",
                "content": "TikTok Shop运营关键点：1) 短视频内容是核心，3秒内抓住注意力；2) 直播带货需提前预热，设置专属优惠；3) 选品要符合TikTok用户画像，年轻化、视觉冲击力强；4) 达人合作是重要引流方式，选择与品牌调性匹配的达人；5) 话题标签策略，参与热门挑战和创建品牌话题；6) 发帖时间选择目标市场活跃时段；7) 数据分析关注播放量、点赞率、评论率、转化率。TikTok Shop目前在美国、英国、东南亚等市场开放。",
                "tags": ["TikTok", "短视频", "直播带货", "达人合作"],
            },
            {
                "title": "多平台铺货策略与风险管控",
                "content": "多平台铺货策略：1) 主力平台选择1-2个深耕，辅助平台3-5个测试；2) 产品差异化定价，不同平台价格策略不同；3) 库存分配要合理，避免平台间库存冲突；4) 客服统一管理，使用ERP系统集中处理；5) 品牌保护，注册各平台品牌备案。风险管控：1) 避免平台关联风险，不同平台使用不同资料；2) 合规经营，了解各平台规则差异；3) 资金分散，避免单一平台收款风险；4) 数据安全，各平台账号独立管理。",
                "tags": ["多平台", "铺货", "风险管控", "品牌保护"],
            },
            {
                "title": "季节性产品运营日历",
                "content": "跨境电商季节性产品运营时间表：1月-新年装饰、冬季保暖；2月-情人节礼品、春节装饰；3月-春季新品、复活节；4月-户外用品、园艺工具；5月-母亲节礼品、夏季准备；6月-父亲节、毕业季、夏季用品；7月-返校季准备、独立日；8月-返校季高峰、秋季准备；9月-万圣节备货、秋季新品；10月-万圣节、感恩节准备；11月-黑五网一、圣诞备货；12月-圣诞节、新年准备。关键原则：提前2-3个月备货，提前1个月开始广告投放，活动期间加大预算。",
                "tags": ["季节性", "运营日历", "备货", "黑五网一"],
            },
        ],
    },
    "platform_rules": {
        "name": "平台规则与政策",
        "description": "各电商平台规则、政策变更、合规要求",
        "documents": [
            {
                "title": "亚马逊账号健康指标",
                "content": "亚马逊账号健康指标(Account Health)是卖家必须关注的核心指标：1) 订单缺陷率(ODR)必须低于1%，包括A-to-Z索赔率、差评率、信用卡拒付率；2) 迟发率必须低于4%；3) 发货前取消率必须低于2.5%；4) 有效追踪率必须高于95%；5) 退货不满意率需关注；6) 违反政策警告需及时处理。账号健康评级分为：绿色(Good)、黄色(Fair)、红色(Poor)。红色状态可能导致账号暂停。建议每周检查账号健康面板，设置自动预警。",
                "tags": ["亚马逊", "账号健康", "ODR", "合规"],
            },
            {
                "title": "亚马逊产品合规要求汇总",
                "content": "亚马逊产品合规要求：1) 电子产品需FCC认证(美国)、CE认证(欧盟)；2) 儿童产品需CPSIA认证、CPC证书；3) 食品接触材料需FDA认证；4) 化妆品需FDA注册和成分声明；5) 医疗器械需FDA 510(k)批准；6) 玩具需ASTM F963测试报告；7) 纺织品需OEKO-TEX认证；8) 电池产品需UN38.3测试报告；9) 激光产品需FDA注册；10) 植物和种子需农业部门许可。上架前务必确认目标市场的合规要求，避免产品被下架或账号被暂停。",
                "tags": ["合规", "认证", "FCC", "CE", "FDA", "CPSIA"],
            },
            {
                "title": "亚马逊知识产权保护政策",
                "content": "亚马逊知识产权保护政策：1) 商标保护：注册品牌备案(Brand Registry)后可使用品牌分析工具和透明计划；2) 版权保护：原创图片、文案受版权保护，可投诉侵权；3) 专利保护：发明专利和外观设计专利均可维权；4) 侵权投诉流程：通过Brand Registry提交侵权投诉，通常3-5个工作日处理；5) 透明计划(Transparency)：防止假货跟卖，每个产品贴唯一码；6) Project Zero：品牌方可直接删除疑似假货listing。建议所有卖家尽早注册品牌备案，这是维权的基础。",
                "tags": ["知识产权", "品牌备案", "侵权", "透明计划"],
            },
            {
                "title": "Shopee平台规则要点",
                "content": "Shopee平台规则要点：1) 违禁品清单：仿冒品、危险品、动植物等禁止销售；2) 评价规则：不能诱导好评或修改差评；3) 发货时效：DTS(Days to Ship)通常为2-3天；4) 退货退款：Shopee担保期内可申请退货；5) 聊天回复率：需保持75%以上；6) 店铺评分：低于4.5星会影响流量；7) 促销活动：参与平台大促可获得流量扶持；8) 本地化要求：部分市场需本地仓发货。注意：东南亚各站点规则略有不同，需分别了解。",
                "tags": ["Shopee", "平台规则", "东南亚", "本地化"],
            },
        ],
    },
    "product_dev": {
        "name": "产品开发与选品",
        "description": "选品方法论、产品生命周期、竞品分析",
        "documents": [
            {
                "title": "数据化选品方法论",
                "content": "数据化选品六步法：1) 市场容量分析：通过Jungle Scout/Helium10查看类目月销量，选择月销10万美金以上的市场；2) 竞争度评估：查看BSR前100的产品评价数量，超过1000评价的产品占比过高则竞争激烈；3) 利润空间计算：售价-FBA费用-佣金-采购成本-头程物流-广告成本=净利润，建议净利润率>20%；4) 差异化空间：分析竞品差评，找到改进点；5) 供应链评估：是否有稳定供应商，MOQ是否可接受；6) 合规风险：确认产品认证要求。选品工具推荐：Helium10、Jungle Scout、Keepa、Seller Sprite。",
                "tags": ["选品", "数据化", "利润计算", "差异化"],
            },
            {
                "title": "产品生命周期管理",
                "content": "跨境电商产品生命周期四阶段：1) 导入期(0-3个月)：重点在产品验证和Listing优化，广告以自动广告为主，收集关键词数据；2) 成长期(3-6个月)：加大广告投入，拓展关键词，提升BSR排名，关注库存管理避免断货；3) 成熟期(6-18个月)：优化利润率，降低ACOS，拓展变体，防御竞品；4) 衰退期(18个月+)：销量持续下滑时，考虑清仓、升级换代或退出。关键指标：导入期关注转化率，成长期关注销量增长，成熟期关注利润率，衰退期关注库存周转。",
                "tags": ["产品生命周期", "导入期", "成长期", "成熟期", "衰退期"],
            },
            {
                "title": "竞品分析框架",
                "content": "竞品分析五维度框架：1) 产品维度：分析竞品的功能、设计、包装、变体策略，找出差异化机会；2) 价格维度：监控竞品价格变化，了解定价策略和促销节奏；3) 流量维度：分析竞品关键词排名、广告策略、流量来源；4) 评价维度：分析竞品评价数量、评分、差评内容，找到产品改进方向；5) 供应链维度：了解竞品的发货方式(FBA/FBM)、库存深度、补货频率。工具推荐：Helium10 Cerebro查关键词、Keepa查价格历史、Seller Sprite查流量词。竞品分析应每月更新一次，大促前加密分析频率。",
                "tags": ["竞品分析", "差异化", "价格策略", "流量分析"],
            },
            {
                "title": "私模产品开发流程",
                "content": "私模产品开发流程：1) 需求验证：通过竞品差评分析和市场调研确认需求；2) 产品设计：与设计师合作完成外观和功能设计，注意专利检索避免侵权；3) 原型制作：3D打印或手工制作原型，测试功能可行性；4) 开模：选择可靠模具厂，确认开模费用(通常1-5万人民币)和周期(15-30天)；5) 样品确认：试模样品确认后进行小批量试产；6) 质量检测：进行可靠性测试、安规测试；7) 批量生产：确认大货质量标准，安排QC验货；8) 上市准备：拍摄产品图、编写Listing、准备FBA发货。私模产品开发周期通常3-6个月，建议同时开发2-3个产品分散风险。",
                "tags": ["私模", "产品开发", "开模", "质量检测"],
            },
        ],
    },
    "advertising": {
        "name": "广告投放与优化",
        "description": "广告策略、出价优化、ROI提升",
        "documents": [
            {
                "title": "亚马逊广告类型与策略",
                "content": "亚马逊广告三大类型：1) SP(Sponsored Products)商品推广：最核心的广告类型，按点击付费，出现在搜索结果和产品详情页。策略：新品期以自动广告为主收集关键词，成长期手动精准投放核心词，成熟期拓展长尾词和ASIN定位。2) SB(Sponsored Brands)品牌推广：展示品牌Logo和自定义文案，出现在搜索结果顶部。策略：用于品牌建设和新品推广，配合品牌旗舰店使用。3) SD(Sponsored Display)展示型推广：再营销和受众定向，出现在产品详情页和站外。策略：用于竞品防御和客户再营销。预算分配建议：SP 70%、SB 20%、SD 10%。",
                "tags": ["亚马逊广告", "SP", "SB", "SD", "预算分配"],
            },
            {
                "title": "关键词出价优化策略",
                "content": "关键词出价优化策略：1) 新词出价：建议从建议出价的75%开始，观察3-5天数据后调整；2) 高转化词：逐步提高出价5%-10%，抢占首页首位；3) 低转化高点击词：降低出价或添加为否定词；4) 长尾词策略：低出价广覆盖，积累数据后筛选优质词；5) 竞品ASIN定位：出价略高于商品推广建议出价；6) 季节性调整：大促前2周提高出价，大促后逐步回调。出价调整频率：日常每3天调整一次，大促期间每天调整。关键指标：ACOS、转化率、点击率(CTR)、展示量。ACOS目标：新品期50%以内，成长期35%以内，成熟期25%以内。",
                "tags": ["出价优化", "关键词", "ACOS", "转化率"],
            },
            {
                "title": "Facebook广告投放指南",
                "content": "Facebook广告投放要点：1) 广告结构：Campaign(目标)→Ad Set(受众)→Ad(创意)，层级管理；2) 受众定位：核心受众(兴趣/行为/人口统计)、自定义受众(网站访客/客户列表)、类似受众(Lookalike 1%-5%)；3) 广告目标选择：品牌认知→流量→互动→转化，根据阶段选择；4) 预算策略：CBO(Campaign Budget Optimization)让系统自动分配预算；5) A/B测试：每次只测试一个变量(素材/受众/文案)；6) 再营销：设置Pixel追踪，对网站访客进行再营销；7) 素材规范：图片1200x628px，视频15-30秒，文案125字符以内。建议日预算至少$20，测试周期5-7天。",
                "tags": ["Facebook", "广告投放", "受众定位", "再营销"],
            },
            {
                "title": "Google Ads购物广告优化",
                "content": "Google Shopping广告优化策略：1) Feed优化：标题包含核心关键词，描述详细准确，图片高质量多角度；2) 出价策略：初期使用Target ROAS自动出价，积累数据后切换Manual CPC精细优化；3) 否定关键词：定期添加不相关搜索词为否定词，减少无效花费；4) 产品细分：按品类/价格/利润率创建不同广告系列；5) 季节性调整：大促前提高出价和预算，添加促销信息；6) 竞品监控：使用第三方工具监控竞品广告展示和价格；7) 本地库存广告：如有线下门店可同步展示库存。关键指标：ROAS目标300%-500%，CTR>0.5%，转化率>2%。",
                "tags": ["Google Ads", "Shopping", "Feed优化", "ROAS"],
            },
        ],
    },
    "logistics_warehouse": {
        "name": "物流与仓储",
        "description": "FBA管理、海外仓、物流成本优化",
        "documents": [
            {
                "title": "FBA库存管理最佳实践",
                "content": "FBA库存管理最佳实践：1) 安全库存计算：日均销量×补货周期×(1+安全系数20%)，补货周期=生产时间+头程物流+入库时间；2) 补货预警：设置库存预警线，低于安全库存自动提醒；3) 库存限制：注意IPI分数影响库存容量，IPI>500可获得更多容量；4) 长期仓储费：超过365天的库存每立方英尺6.9美元或每件0.15美元(取较高值)，建议在270天时启动清仓计划；5) 断货应对：断货前提高价格减少销量，断货期间保持广告投放维持排名，补货后用Coupon和广告快速恢复；6) 库存周转：目标周转天数60-90天，过高占用资金，过低容易断货。工具推荐：FBA Calculator、Inventory Manager。",
                "tags": ["FBA", "库存管理", "补货", "IPI", "长期仓储费"],
            },
            {
                "title": "海外仓运营指南",
                "content": "海外仓运营指南：1) 仓址选择：美国(美西洛杉矶/美东新泽西)、欧洲(英国/德国)、澳洲(悉尼/墨尔本)；2) 入仓流程：头程海运/空运→清关→入仓上架(1-3天)；3) 订单处理：接收订单→拣货→打包→发货(24小时内)；4) 库存管理：WMS系统管理，支持多SKU多库位；5) 退换货处理：接收退货→质检→重新上架或销毁；6) 成本结构：仓储费+操作费+尾程配送费，综合成本比FBA低15%-30%；7) 系统对接：与ERP/OMS/WMS系统对接，实现订单自动推送和库存同步。海外仓适合：体积大/重量大的产品、多平台铺货、需要快速配送的产品。",
                "tags": ["海外仓", "仓储", "WMS", "尾程配送"],
            },
            {
                "title": "头程物流方案对比",
                "content": "头程物流方案对比：1) 国际快递(DHL/FedEx/UPS)：时效3-5天，成本最高($5-8/kg)，适合紧急补货和样品；2) 空运：时效7-12天，成本中等($3-5/kg)，适合轻小件和高价值产品；3) 海运整柜(FCL)：时效25-40天，成本最低($800-1500/柜)，适合大批量稳定出货；4) 海运拼柜(LCL)：时效30-45天，成本较低($50-80/CBM)，适合中小批量；5) 铁路(中欧班列)：时效18-25天，成本适中，适合欧洲市场；6) 卡航：时效12-18天，成本介于空运和海运之间。选择建议：根据产品特性、时效要求和成本预算综合选择，建议组合使用多种方案。",
                "tags": ["头程物流", "海运", "空运", "快递", "成本对比"],
            },
            {
                "title": "FBA货件创建与发货流程",
                "content": "FBA货件创建与发货流程：1) 转为FBA发货：在库存管理中选择'转为FBA发货'；2) 货件创建：填写发货地址、包装信息，选择配送计划(单点/多点入仓)；3) 打印标签：产品贴FNSKU标签，外箱贴货件标签；4) 预处理：产品需符合FBA包装要求，套袋/气泡膜/集束包装等；5) 选择承运人：小包裹用UPS/FedEx，零担用LTL；6) 发货追踪：在货件中填写追踪号，跟踪物流状态；7) 入库确认：亚马逊接收后1-3天可售。注意事项：货件需在30天内送达，超时可能被取消；准确填写装箱信息避免入库延迟；高价值产品建议购买运输保险。",
                "tags": ["FBA", "货件", "发货流程", "入库"],
            },
        ],
    },
    "finance_compliance": {
        "name": "财务与合规",
        "description": "成本核算、税务合规、资金管理",
        "documents": [
            {
                "title": "跨境电商成本核算模型",
                "content": "跨境电商成本核算模型：1) 产品成本：采购价+包装费+国内物流费；2) 头程物流：海运/空运/快递费用，分摊到单件；3) 平台佣金：亚马逊15%(大部分类目)、Shopee6%-8%、独立站0%(但有支付手续费2%-3%)；4) FBA费用：配送费(按尺寸重量)+月仓储费+长期仓储费；5) 广告成本：ACOS×售价=单件广告成本；6) 退货成本：退货率×(产品成本+FBA配送费+退货处理费)；7) 其他费用：VAT/关税、汇率损失、平台订阅费。利润计算：售价-产品成本-头程物流-佣金-FBA费用-广告成本-退货成本-其他费用=净利润。建议净利润率>15%，低于10%需优化成本结构。",
                "tags": ["成本核算", "利润计算", "FBA费用", "佣金"],
            },
            {
                "title": "跨境电商税务合规指南",
                "content": "跨境电商税务合规要点：1) 美国市场：各州销售税(Sales Tax)不同，需注册销售税许可证并在有Nexus的州申报；2) 欧盟市场：VAT(增值税)需在目标国注册，OSS(一站式申报)简化流程，标准税率17%-27%；3) 英国市场：脱欧后需单独注册英国VAT，标准税率20%；4) 日本市场：JCT(日本消费税)2023年10月起实施，税率10%；5) 东南亚：各国VAT/GST不同，泰国7%、越南10%、印尼11%。合规建议：1) 及时注册目标市场税号；2) 准确计算和申报税款；3) 保留完整交易记录；4) 使用专业税务软件辅助申报；5) 定期关注税法变化。",
                "tags": ["税务合规", "VAT", "销售税", "JCT"],
            },
            {
                "title": "跨境收款与资金管理",
                "content": "跨境收款方案对比：1) Payoneer(派安盈)：支持亚马逊/Shopee等平台，费率1%-2%，提现1-2天到账；2) PingPong：费率1%起，支持多平台，到账快；3) 万里汇(WorldFirst)：费率1%起，阿里系，适合阿里平台；4) LianLian Pay：费率0.7%起，支持多币种；5) 直接银行转账：费率低但到账慢(3-5天)。资金管理建议：1) 多币种账户管理，减少汇率损失；2) 分散收款渠道，降低单一渠道风险；3) 定期结汇，关注汇率走势；4) 预留运营资金，避免资金链断裂；5) 合规申报，避免税务风险。建议使用2-3个收款渠道，主渠道处理日常收款，备用渠道应急。",
                "tags": ["跨境收款", "Payoneer", "PingPong", "资金管理"],
            },
            {
                "title": "跨境电商财务报表体系",
                "content": "跨境电商财务报表体系：1) 利润表：按SKU/店铺/平台维度，计算收入-成本-费用=利润；2) 现金流量表：跟踪资金流入流出，关注回款周期(亚马逊14天/其他平台7-30天)；3) 库存报表：库存金额/数量/周转天数/滞销品占比；4) 广告报表：广告花费/ACOS/ROAS/各广告组表现；5) 退货报表：退货率/退货原因/退货成本；6) 平台费用报表：佣金/FBA费用/仓储费/其他扣费明细。关键指标：毛利率(>40%)、净利润率(>15%)、库存周转天数(60-90天)、现金流转周期(<45天)。建议每周更新核心指标看板，每月出具完整财务报表。",
                "tags": ["财务报表", "利润表", "现金流量", "库存周转"],
            },
        ],
    },
}


def init_db():
    conn = psycopg2.connect(host=_PG_HOST, port=_PG_PORT, user=_PG_USER, password=_PG_PASS, dbname=_PG_DB)
    import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
    c.execute("""CREATE TABLE IF NOT EXISTS knowledge_documents (
        id SERIAL PRIMARY KEY,
        doc_id TEXT UNIQUE,
        title TEXT,
        category TEXT,
        content TEXT,
        tags TEXT,
        source TEXT DEFAULT 'builtin',
        char_count INTEGER DEFAULT 0,
        chunk_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at TEXT,
        updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS knowledge_chunks (
        id SERIAL PRIMARY KEY,
        chunk_id TEXT UNIQUE,
        doc_id TEXT,
        chunk_index INTEGER,
        content TEXT,
        char_count INTEGER DEFAULT 0,
        vector BYTEA,
        created_at TEXT,
        FOREIGN KEY (doc_id) REFERENCES knowledge_documents(doc_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS hallucination_checks (
        id SERIAL PRIMARY KEY,
        query TEXT,
        response TEXT,
        sources TEXT,
        confidence_score REAL DEFAULT 0.0,
        hallucination_risk TEXT DEFAULT 'low',
        check_details TEXT,
        checked_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS import_logs (
        id SERIAL PRIMARY KEY,
        import_id TEXT,
        source_type TEXT,
        source_path TEXT,
        total_docs INTEGER DEFAULT 0,
        imported_docs INTEGER DEFAULT 0,
        failed_docs INTEGER DEFAULT 0,
        total_chunks INTEGER DEFAULT 0,
        status TEXT DEFAULT 'running',
        started_at TEXT,
        completed_at TEXT,
        error_message TEXT
    )""")
    conn.commit()
    conn.close()


def get_db():
    conn = psycopg2.connect(host=_PG_HOST, port=_PG_PORT, user=_PG_USER, password=_PG_PASS, dbname=_PG_DB)
    return conn


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """文本分块算法：按句号/感叹号/问号等边界进行智能切分，块间重叠保证上下文语义连贯"""

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        split_pos = end
        for sep in ["。", ".", "！", "!", "？", "%s", "\n", "；", ";"]:
            pos = text.rfind(sep, start + chunk_size // 2, end)
            if pos > start:
                split_pos = pos + 1
                break

        chunks.append(text[start:split_pos])
        start = split_pos - overlap
        if start < 0:
            start = 0

    return chunks


def generate_doc_id(title: str, category: str) -> str:
    raw = f"{category}:{title}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def generate_chunk_id(doc_id: str, chunk_index: int) -> str:
    return f"{doc_id}-{chunk_index:04d}"


def generate_vector(text: str) -> List[float]:
    """生成文本向量：优先使用sentence-transformers，不可用时使用确定性伪随机向量"""

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
    except Exception:
        import random
        random.seed(hash(text) % (2**31))
        return [random.gauss(0, 1) for _ in range(VECTOR_DIM)]


def calculate_text_similarity(query: str, text: str) -> float:
    """文本相似度算法（词袋模型）：中英文令牌化后计算Jaccard相似度"""

    def tokenize(s: str) -> set:
        tokens = set()
        words = re.findall(r"[a-zA-Z0-9]+", s.lower())
        tokens.update(words)
        cn_chars = re.findall(r"[\u4e00-\u9fff]", s)
        tokens.update(cn_chars)
        cn_words = re.findall(r"[\u4e00-\u9fff]{2,}", s)
        tokens.update(cn_words)
        for w in cn_words:
            for i in range(len(w)):
                for j in range(i + 1, min(i + 4, len(w) + 1)):
                    tokens.add(w[i:j])
        return tokens

    query_tokens = tokenize(query)
    text_tokens = tokenize(text)
    if not query_tokens:
        return 0.0
    intersection = query_tokens & text_tokens
    return len(intersection) / len(query_tokens)


class HallucinationDetector:
    """幻觉检测器：评估回答在知识来源中的覆盖度、事实一致性、完整性，判定幻觉风险等级"""
    def __init__(self):
        self.min_confidence = 0.3
        self.high_risk_threshold = 0.5
        self.medium_risk_threshold = 0.7

    def check(self, query: str, response: str, sources: List[Dict]) -> Dict:
        """幻觉检测主流程：计算source_coverage*0.4 + factual_consistency*0.4 + completeness*0.2"""

        if not sources:
            return {
                "confidence_score": 0.0,
                "hallucination_risk": "high",
                "details": {
                    "reason": "无知识来源支撑",
                    "source_coverage": 0.0,
                    "factual_consistency": 0.0,
                    "completeness": 0.0,
                },
                "recommendation": "拒绝回答或明确声明无法确认",
            }

        source_texts = [s.get("content", "") for s in sources]
        source_coverage = self._calculate_source_coverage(response, source_texts)
        factual_consistency = self._calculate_factual_consistency(query, response, source_texts)
        completeness = self._calculate_completeness(query, sources)

        confidence = source_coverage * 0.4 + factual_consistency * 0.4 + completeness * 0.2

        if confidence < self.high_risk_threshold:
            risk = "high"
        elif confidence < self.medium_risk_threshold:
            risk = "medium"
        else:
            risk = "low"

        recommendation = self._get_recommendation(risk, confidence)

        return {
            "confidence_score": round(confidence, 3),
            "hallucination_risk": risk,
            "details": {
                "source_coverage": round(source_coverage, 3),
                "factual_consistency": round(factual_consistency, 3),
                "completeness": round(completeness, 3),
            },
            "recommendation": recommendation,
        }

    def _calculate_source_coverage(self, response: str, source_texts: List[str]) -> float:
        if not response:
            return 0.0
        response_words = set(re.findall(r"\w+", response.lower()))
        if not response_words:
            return 0.0

        all_source_words = set()
        for text in source_texts:
            all_source_words.update(re.findall(r"\w+", text.lower()))

        covered = response_words & all_source_words
        return len(covered) / len(response_words)

    def _calculate_factual_consistency(self, query: str, response: str, source_texts: List[str]) -> float:
        if not source_texts:
            return 0.0

        scores = []
        for source_text in source_texts:
            score = calculate_text_similarity(response, source_text)
            scores.append(score)

        return max(scores) if scores else 0.0

    def _calculate_completeness(self, query: str, sources: List[Dict]) -> float:
        if not sources:
            return 0.0

        top_scores = sorted([s.get("score", 0) for s in sources], reverse=True)
        if not top_scores:
            return 0.0

        top_score = top_scores[0]
        if top_score >= 0.8:
            return 1.0
        elif top_score >= 0.5:
            return 0.7
        elif top_score >= 0.3:
            return 0.4
        return 0.2

    def _get_recommendation(self, risk: str, confidence: float) -> str:
        if risk == "high":
            return "高幻觉风险：建议拒绝回答或明确标注信息来源不确定"
        elif risk == "medium":
            return "中等幻觉风险：建议标注信息来源，提醒用户核实"
        return "低幻觉风险：回答可信度较高，建议附上参考来源"


class KnowledgePipeline:
    """知识库管道：管理内置/自定义文档的导入、检索、幻觉检测"""
    def __init__(self):
        init_db()
        self.hallucination_detector = HallucinationDetector()

    def import_builtin_knowledge(self) -> Dict:
        """导入内置电商知识库到PostgreSQL，已存在文档自动更新"""
        import_id = f"import-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_docs = 0
        imported_docs = 0
        failed_docs = 0
        total_chunks = 0

        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            "INSERT INTO import_logs (import_id, source_type, source_path, total_docs, status, started_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (import_id, "builtin", "ECOMMERCE_KNOWLEDGE", 0, "running", now),
        )
        conn.commit()

        for category_key, category_data in ECOMMERCE_KNOWLEDGE.items():
            for doc in category_data["documents"]:
                total_docs += 1
                try:
                    doc_id = generate_doc_id(doc["title"], category_key)
                    content = doc["content"]
                    tags = json.dumps(doc.get("tags", []), ensure_ascii=False)
                    chunks = chunk_text(content)

                    c.execute(
                        "SELECT id FROM knowledge_documents WHERE doc_id = %s",
                        (doc_id,),
                    )
                    existing = c.fetchone()

                    if existing:
                        c.execute(
                            "UPDATE knowledge_documents SET title=%s, category=%s, content=%s, tags=%s, char_count=%s, chunk_count=%s, updated_at=%s WHERE doc_id=%s",
                            (doc["title"], category_key, content, tags, len(content), len(chunks), now, doc_id),
                        )
                        c.execute("DELETE FROM knowledge_chunks WHERE doc_id=%s", (doc_id,))
                    else:
                        c.execute(
                            "INSERT INTO knowledge_documents (doc_id, title, category, content, tags, source, char_count, chunk_count, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (doc_id, doc["title"], category_key, content, tags, "builtin", len(content), len(chunks), "active", now, now),
                        )

                    for i, chunk in enumerate(chunks):
                        chunk_id = generate_chunk_id(doc_id, i)
                        c.execute(
                            "INSERT INTO knowledge_chunks (chunk_id, doc_id, chunk_index, content, char_count, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                            (chunk_id, doc_id, i, chunk, len(chunk), now),
                        )

                    imported_docs += 1
                    total_chunks += len(chunks)
                except Exception as e:
                    failed_docs += 1

        c.execute(
            "UPDATE import_logs SET total_docs=%s, imported_docs=%s, failed_docs=%s, total_chunks=%s, status=%s, completed_at=%s WHERE import_id=%s",
            (total_docs, imported_docs, failed_docs, total_chunks, "completed", now, import_id),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "import_id": import_id,
            "total_docs": total_docs,
            "imported_docs": imported_docs,
            "failed_docs": failed_docs,
            "total_chunks": total_chunks,
        }

    def import_document(self, title: str, category: str, content: str, tags: List[str] = None, source: str = "manual") -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        doc_id = generate_doc_id(title, category)
        chunks = chunk_text(content)
        tags_json = json.dumps(tags or [], ensure_ascii=False)

        try:
            c.execute(
                "INSERT INTO knowledge_documents (doc_id, title, category, content, tags, source, char_count, chunk_count, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (doc_id, title, category, content, tags_json, source, len(content), len(chunks), "active", now, now),
            )

            for i, chunk in enumerate(chunks):
                chunk_id = generate_chunk_id(doc_id, i)
                c.execute(
                    "INSERT INTO knowledge_chunks (chunk_id, doc_id, chunk_index, content, char_count, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (chunk_id, doc_id, i, chunk, len(chunk), now),
                )

            conn.commit()
            conn.close()
            return {"success": True, "doc_id": doc_id, "chunks": len(chunks)}
        except Exception as _pg_ie:
            conn.rollback()
            if 'Duplicate' not in str(_pg_ie) and 'unique' not in str(_pg_ie).lower():
                raise
            c.execute(
                "UPDATE knowledge_documents SET title=%s, content=%s, tags=%s, char_count=%s, chunk_count=%s, updated_at=%s WHERE doc_id=%s",
                (title, content, tags_json, len(content), len(chunks), now, doc_id),
            )
            c.execute("DELETE FROM knowledge_chunks WHERE doc_id=%s", (doc_id,))
            for i, chunk in enumerate(chunks):
                chunk_id = generate_chunk_id(doc_id, i)
                c.execute(
                    "INSERT INTO knowledge_chunks (chunk_id, doc_id, chunk_index, content, char_count, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (chunk_id, doc_id, i, chunk, len(chunk), now),
                )
            conn.commit()
            conn.close()
            return {"success": True, "doc_id": doc_id, "chunks": len(chunks), "updated": True}
        except Exception as e:
            conn.close()
            return {"success": False, "error": str(e)}

    def search(self, query: str, top_k: int = 5, category: str = None) -> Dict:
        """知识检索：按类目过滤 + 文本相似度排序，返回top_k结果"""
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)

        if category:
            c.execute(
                "SELECT chunk_id, doc_id, chunk_index, content FROM knowledge_chunks WHERE doc_id IN (SELECT doc_id FROM knowledge_documents WHERE category = %s AND status = 'active')",
                (category,),
            )
        else:
            c.execute(
                "SELECT chunk_id, doc_id, chunk_index, content FROM knowledge_chunks WHERE doc_id IN (SELECT doc_id FROM knowledge_documents WHERE status = 'active')",
            )

        all_chunks = c.fetchall()
        conn.close()

        if not all_chunks:
            return {"success": True, "query": query, "results": [], "count": 0, "mode": "local_db"}

        scored = []
        for chunk in all_chunks:
            score = calculate_text_similarity(query, chunk["content"])
            if score > 0:
                c2 = get_db()
                import psycopg2.extras as _pg_e; c2_cur = c2.cursor(cursor_factory=_pg_e.RealDictCursor)
                c2_cur.execute("SELECT title, category, tags FROM knowledge_documents WHERE doc_id = %s", (chunk["doc_id"],))
                doc_info = c2_cur.fetchone()
                c2.close()

                scored.append({
                    "score": round(score, 3),
                    "content": chunk["content"],
                    "chunk_index": chunk["chunk_index"],
                    "doc_id": chunk["doc_id"],
                    "title": doc_info["title"] if doc_info else "",
                    "category": doc_info["category"] if doc_info else "",
                    "tags": json.loads(doc_info["tags"]) if doc_info and doc_info["tags"] else [],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        results = scored[:top_k]

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "mode": "local_db",
        }

    def search_with_hallucination_check(self, query: str, response: str, top_k: int = 5, category: str = None) -> Dict:
        """检索+幻觉检测一体：先检索知识库，再检测回答的幻觉风险"""

        search_result = self.search(query, top_k, category)

        hallucination_result = self.hallucination_detector.check(
            query, response, search_result.get("results", [])
        )

        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO hallucination_checks (query, response, sources, confidence_score, hallucination_risk, check_details, checked_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                query,
                response,
                json.dumps([r.get("title", "") for r in search_result.get("results", [])], ensure_ascii=False),
                hallucination_result["confidence_score"],
                hallucination_result["hallucination_risk"],
                json.dumps(hallucination_result["details"], ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "query": query,
            "search_results": search_result.get("results", []),
            "hallucination_check": hallucination_result,
        }

    def get_stats(self) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)

        c.execute("SELECT COUNT(*) as total FROM knowledge_documents WHERE status='active'")
        doc_count = c.fetchone()["total"]

        c.execute("SELECT COUNT(*) as total FROM knowledge_chunks")
        chunk_count = c.fetchone()["total"]

        c.execute("SELECT category, COUNT(*) as count FROM knowledge_documents WHERE status='active' GROUP BY category")
        category_stats = [dict(row) for row in c.fetchall()]

        c.execute("SELECT COUNT(*) as total FROM hallucination_checks")
        check_count = c.fetchone()["total"]

        c.execute("SELECT hallucination_risk, COUNT(*) as count FROM hallucination_checks GROUP BY hallucination_risk")
        risk_stats = [dict(row) for row in c.fetchall()]

        conn.close()

        return {
            "success": True,
            "documents": doc_count,
            "chunks": chunk_count,
            "categories": category_stats,
            "hallucination_checks": check_count,
            "risk_distribution": risk_stats,
        }

    def list_categories(self) -> Dict:
        categories = {}
        for key, data in ECOMMERCE_KNOWLEDGE.items():
            categories[key] = {
                "name": data["name"],
                "description": data["description"],
                "document_count": len(data["documents"]),
            }

        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("SELECT category, COUNT(*) as count FROM knowledge_documents WHERE status='active' GROUP BY category")
        db_stats = {row["category"]: row["count"] for row in c.fetchall()}
        conn.close()

        for key in categories:
            categories[key]["imported_count"] = db_stats.get(key, 0)

        return {"success": True, "categories": categories, "total_categories": len(categories)}

    def delete_document(self, doc_id: str) -> Dict:
        conn = get_db()
        import psycopg2.extras as _pg_e; c = conn.cursor(cursor_factory=_pg_e.RealDictCursor)
        c.execute("UPDATE knowledge_documents SET status='deleted' WHERE doc_id=%s", (doc_id,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "doc_id": doc_id, "deleted": affected > 0}


def main():
    """CLI入口：根据action参数路由到知识导入/检索/幻觉检测/统计等子模块"""
    input_data = json.loads(sys.stdin.read())
    action = input_data.get("action", "search")
    pipeline = KnowledgePipeline()

    if action == "import_builtin":
        result = pipeline.import_builtin_knowledge()

    elif action == "import_document":
        result = pipeline.import_document(
            title=input_data.get("title", ""),
            category=input_data.get("category", ""),
            content=input_data.get("content", ""),
            tags=input_data.get("tags", []),
            source=input_data.get("source", "manual"),
        )

    elif action == "search":
        result = pipeline.search(
            query=input_data.get("query", ""),
            top_k=input_data.get("top_k", 5),
            category=input_data.get("category"),
        )

    elif action == "search_with_check":
        result = pipeline.search_with_hallucination_check(
            query=input_data.get("query", ""),
            response=input_data.get("response", ""),
            top_k=input_data.get("top_k", 5),
            category=input_data.get("category"),
        )

    elif action == "stats":
        result = pipeline.get_stats()

    elif action == "list_categories":
        result = pipeline.list_categories()

    elif action == "delete_document":
        result = pipeline.delete_document(input_data.get("doc_id", ""))

    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
