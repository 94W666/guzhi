# -*- coding: utf-8 -*-
"""Generate investment guru educational commentary based on fund metrics.

Each guru's philosophy is explained in relation to the fund's data —
educational only, no investment advice or recommendations.
"""


def generate_commentary(fund_name, fund_type, metrics, holdings_count):
    """Generate educational commentary referencing investment masters.

    Returns a list of {master, avatar, style, comment} dicts.
    No verdict field — compliance: data presentation only, no conclusions.
    """
    commentators = []

    ret_1y = metrics.get('returns', {}).get('1y')
    ret_3y = metrics.get('returns', {}).get('3y')
    ret_5y = metrics.get('returns', {}).get('5y')

    mdd_1y = metrics.get('max_drawdown', {}).get('1y', {}).get('mdd')
    mdd_3y = metrics.get('max_drawdown', {}).get('3y', {}).get('mdd')
    mdd_all = metrics.get('max_drawdown', {}).get('since_inception', {}).get('mdd')

    vol_1y = metrics.get('volatility', {}).get('1y')
    sharpe_1y = metrics.get('sharpe', {}).get('1y')
    sharpe_3y = metrics.get('sharpe', {}).get('3y')

    win_1y = metrics.get('win_rate', {}).get('1y')
    calmar_1y = metrics.get('calmar', {}).get('1y')
    calmar_3y = metrics.get('calmar', {}).get('3y')

    pe = metrics.get('pe_ratio', {}).get('pe')

    commentators.append(_buffett(ret_1y, ret_3y, ret_5y, mdd_all, vol_1y, sharpe_3y, pe))
    commentators.append(_munger(ret_3y, ret_5y, mdd_3y, mdd_all, win_1y, calmar_3y))
    commentators.append(_duan(ret_1y, ret_3y, mdd_all, pe, holdings_count))
    commentators.append(_lynch(ret_1y, ret_3y, pe, vol_1y, win_1y))
    commentators.append(_bogle(fund_name, ret_3y, ret_5y, vol_1y, sharpe_3y, fund_type))
    commentators.append(_marks(ret_1y, mdd_1y, mdd_all, vol_1y, calmar_1y))

    return commentators


# ---------------------------------------------------------------------------
# Individual guru logic — educational framing, no fund-specific verdicts
# ---------------------------------------------------------------------------

def _buffett(r1, r3, r5, mdd_all, vol, sr3, pe):
    style = '价值投资 \u00b7 护城河 \u00b7 长期持有'
    lines = []

    lines.append(
        '巴菲特的投资方法核心是寻找具有持久竞争优势的企业，以合理的价格买入并长期持有。'
        '他关注以下指标来辅助判断：'
    )

    if pe is not None:
        if pe < 15:
            lines.append(
                'PE 仅 %.1f，处于较低水平。巴菲特通常关注 PE：估值低时安全边际更高，'
                '但低 PE 不等于好投资——需要结合企业的护城河、盈利稳定性综合判断。' % pe
            )
        elif pe < 25:
            lines.append(
                'PE %.1f，处于中等水平。巴菲特会进一步考察企业的竞争优势是否可持续，'
                '以及管理层是否值得信任。估值合理时，企业质量是决定性因素。' % pe
            )
        else:
            lines.append(
                'PE %.1f，估值偏高。巴菲特倾向于在市场价格低于内在价值时出手，'
                '高估值意味着需要更高的未来增长来消化。不过他也说过："以合理价格买入伟大企业，'
                '胜过以便宜价格买入平庸企业。"' % pe
            )
    else:
        lines.append('PE 数据缺失。巴菲特重视企业的估值水平，但更重视企业的"护城河"——即竞争对手难以复制的优势。')

    if r5 is not None:
        lines.append(
            '5 年年化收益 %.1f%%。巴菲特认为长期收益体现了企业的复利能力，'
            '但更重要的是能否持续。过去的收益不等同于未来表现。' % (r5 * 100)
        )

    if r3 is not None and r5 is not None and r3 > 0.08 and r5 > 0.08:
        lines.append(
            '3 年和 5 年回报均为正值，长期来看企业为投资者创造了价值。'
            '巴菲特强调：股票长期是称重机——最终价格会反映企业真实价值。'
        )

    if mdd_all is not None and abs(mdd_all) > 0.4:
        lines.append(
            '自成立最大回撤约 %.0f%%。巴菲特认为波动不是风险，永久性资本损失才是。'
            '关键不在于回撤多大，而在于你对所持资产有多了解。' % (abs(mdd_all) * 100)
        )

    if vol is not None:
        lines.append(
            '年化波动率 %.1f%%。巴菲特不把波动视为风险——他认为风险是"不知道自己在做什么"。'
            '如果你理解所持企业，短期价格波动只是噪音。' % (vol * 100)
        )

    return {
        'master': '沃伦\u00b7巴菲特',
        'avatar': 'B',
        'style': style,
        'comment': '\n\n'.join(lines),
    }


def _munger(r3, r5, mdd_3, mdd_all, win, calmar_3):
    style = '逆向思维 \u00b7 能力圈 \u00b7 心智模型'
    lines = []

    lines.append(
        '芒格的投资哲学强调逆向思维和多学科心智模型。'
        '他关注风险控制和人的行为偏差，以下是相关指标：'
    )

    if mdd_3 is not None:
        if abs(mdd_3) < 0.15:
            lines.append(
                '3 年最大回撤仅 %.1f%%，波动较小。芒格常说："如果一件事不值得做，'
                '那就不值得做好。"他重视的是投资决策的质量，而非短期波动。' % (abs(mdd_3) * 100)
            )
        elif abs(mdd_3) < 0.30:
            lines.append(
                '3 年最大回撤 %.1f%%，波动适中。芒格认为：承受一定波动是获取长期回报的代价，'
                '重要的是你能否在下跌时保持理性，不因恐慌而做出错误决策。' % (abs(mdd_3) * 100)
            )
        else:
            lines.append(
                '3 年最大回撤 %.1f%%，波动较大。芒格的投资准则之一：'
                '"倒过来想，总是倒过来想。"——大跌时应该问的不是"要不要卖"，'
                '而是"当初为什么买？这个理由还在不在？"' % (abs(mdd_3) * 100)
            )
    else:
        lines.append('芒格重视风险：他常说"如果我知道我会死在哪里，我就永远不去那个地方。"了解基金的回撤特征，有助于评估它是否在你可承受的范围内。')

    if mdd_all is not None and abs(mdd_all) > 0.45:
        lines.append(
            '自成立最大回撤 %.0f%%。芒格提醒：极端事件总会发生，'
            '关键是事先做好心理准备，而不是在恐慌中做决策。' % (abs(mdd_all) * 100)
        )

    if win is not None:
        lines.append(
            '胜率 %.1f%%。芒格关注的是决策过程的质量而非结果的随机分布。'
            '胜率高低只是描述性数据，不构成对未来走势的判断。' % (win * 100)
        )

    if calmar_3 is not None:
        lines.append(
            'Calmar 比率 %.1f，衡量了收益与回撤的关系。芒格的理念中，"避开蠢事比做聪明事更重要"。'
            '关注风险调整后的效率是一种理性投资态度。' % calmar_3
        )

    return {
        'master': '查理\u00b7芒格',
        'avatar': 'M',
        'style': style,
        'comment': '\n\n'.join(lines),
    }


def _duan(r1, r3, mdd_all, pe, hc):
    style = '买企业就是买股权 \u00b7 不择时 \u00b7 看商业模式'
    lines = []

    lines.append(
        '段永平的投资理念：买股票就是买企业的一部分。'
        '他只投资自己能看懂的公司，不预测市场。以下是相关数据参考：'
    )

    if r3 is not None:
        if r3 > 0.15:
            lines.append(
                '3 年年化 %.1f%%。段永平认为投资的核心不是看收益率，'
                '而是看企业的商业模式是否优秀。好的商业模式是长期收益的根本来源。' % (r3 * 100)
            )
        elif r3 > 0.05:
            lines.append(
                '3 年年化 %.1f%%。段永平常说："我不关心短期波动，'
                '我只关心这个生意能不能做 10 年。"收益率只是企业经营的副产品。' % (r3 * 100)
            )
        else:
            lines.append(
                '3 年年化 %.1f%%。段永平的投资经历表明：短期低迷不代表什么。'
                '他曾在网易下跌 50%% 时继续持有，因为他看懂了这个企业的价值。' % (r3 * 100)
            )
    else:
        lines.append('段永平的核心判断标准很简单：看得懂就投，看不懂就不投。这和打游戏一样——只玩自己会玩的。')

    if r1 is not None:
        if r1 > 0.50:
            lines.append(
                '近 1 年涨幅约 %.0f%%。段永平不因短期大涨而追高——"好价格比好时机重要"。'
                '他关注的是企业本身，而非股价走势。' % (r1 * 100)
            )
        elif r1 < -0.10:
            lines.append(
                '近 1 年跌幅约 %.0f%%。段永平的经验是：如果你真的看懂了企业，'
                '价格下跌意味着可以用更低的价格买入——前提是你对企业的判断是正确的。' % (abs(r1) * 100)
            )

    if hc > 0:
        lines.append(
            '该基金持有 %d 只股票。段永平的方法是逐一研究持仓企业的商业模式，'
            '判断这些企业是否有持续的竞争优势。' % hc
        )

    if pe is not None and pe > 40:
        lines.append(
            'PE %.0f 较高。段永平认为高 PE 本身不可怕，关键是企业未来的增长能否支撑这个估值。'
            '"如果你能看 10 年，很多问题就变得简单了。"' % pe
        )

    if mdd_all is not None and abs(mdd_all) > 0.40:
        lines.append(
            '历史上最大回撤约 %.0f%%。段永平的理念：如果你不知道企业值多少钱，'
            '任何波动都会让你恐慌。知道自己买的是什么，才能在波动中保持定力。' % (abs(mdd_all) * 100)
        )

    return {
        'master': '段永平',
        'avatar': 'D',
        'style': style,
        'comment': '\n\n'.join(lines),
    }


def _lynch(r1, r3, pe, vol, win):
    style = '成长股猎手 \u00b7 PEG \u00b7 自下而上'
    lines = []

    lines.append(
        '彼得·林奇以挖掘成长股著称，他提出的 PEG（市盈率/增长率）是评估成长估值的经典工具。'
        '他还主张从日常生活中发现投资机会。以下是相关数据：'
    )

    if pe is not None and r3 is not None and r3 > 0:
        peg = pe / (r3 * 100)
        if peg < 1:
            lines.append(
                '粗略 PEG 约 %.1f（PE / 3年增速）。林奇认为 PEG < 1 时，'
                '增长没有充分反映在估值中。但需注意：PEG 只是一种粗略参考，'
                '历史增速不代表未来。' % peg
            )
        elif peg < 2:
            lines.append(
                '粗略 PEG 约 %.1f，处于中间水平。林奇会进一步研究企业的盈利增长可持续性，'
                '而不仅看一个比率。合理的成长股投资需要深入的基本面分析。' % peg
            )
        else:
            lines.append(
                '粗略 PEG 约 %.1f，偏高。林奇认为此时需要更细致的分析——'
                '企业是否有独特的产品或市场地位来支撑高估值增长？PEG 只是起点。' % peg
            )
    elif pe is not None:
        lines.append(
            'PE 为 %.1f。缺少增长数据无法计算 PEG。林奇的方法强调：'
            '投资的关键是理解企业的增长故事——它的产品受欢迎吗？市场空间有多大？' % pe
        )

    if r1 is not None and vol is not None:
        lines.append(
            '近 1 年回报 %.1f%%，波动率 %.1f%%。林奇根据成长性和风险特征将股票分为六类：'
            '缓慢增长型、稳健增长型、快速增长型、周期型、困境反转型和隐蔽资产型。'
            '不同类型的投资策略有所不同。' % (r1 * 100, vol * 100)
        )

    if win is not None:
        if win > 0.55:
            lines.append(
                '胜率 %.1f%%，大部分交易日上涨。林奇指出：即使是一只好股票，'
                '也不可能每天都涨。关键在于企业基本面是否在持续改善。' % (win * 100)
            )
        elif win < 0.45:
            lines.append(
                '胜率 %.1f%%，上涨天数较少。林奇的建议是：关注企业的盈利能力，'
                '而非股价的每日波动。短期市场是投票机，长期是称重机。' % (win * 100)
            )

    return {
        'master': '彼得\u00b7林奇',
        'avatar': 'L',
        'style': style,
        'comment': '\n\n'.join(lines),
    }


def _bogle(name, r3, r5, vol, sr, ftype):
    style = '指数基金 \u00b7 低成本 \u00b7 长期持有'
    lines = []

    is_index = any(kw in (name or '') for kw in ['指数', 'ETF', '标普', '500'])

    lines.append(
        '约翰·博格是指数基金之父，他主张大多数投资者应该买入低成本、'
        '分散化的指数基金，然后长期持有，不频繁交易。'
    )

    if is_index:
        lines.append(
            '这是一只指数型基金。博格一生都在倡导指数的力量：'
            '"不要去找那根针，直接买下整个草堆。"指数基金天然分散了单只股票的风险。'
        )

    if r5 is not None:
        lines.append(
            '5 年年化收益 %.1f%%。博格强调费用率的重要性：'
            '"复利的神奇力量会被高额的基金管理费蚕食。"他建议关注基金的总费用比率。' % (r5 * 100)
        )

    if r3 is not None:
        lines.append(
            '3 年年化 %.1f%%。博格的投资哲学核心是"常识投资"——'
            '保持简单、保持耐心、保持纪律。不择时、不追逐热门基金。' % (r3 * 100)
        )

    if sr is not None:
        if sr > 1.5:
            lines.append(
                '夏普比率 %.1f，风险调整后收益较好。博格会提醒：历史数据不能预测未来。'
                '"投资的四个字真言：坚持到底。"' % sr
            )
        elif sr < 0.5:
            lines.append(
                '夏普比率 %.1f。博格的核心关注点不在收益率或比率，而在费用——'
                '每年多付 1%% 的管理费，30 年可能损失超过三分之一的总回报。' % sr
            )

    if not lines:
        lines.append('博格的信条："时间是投资者的朋友，冲动是投资者的敌人。"')

    return {
        'master': '约翰\u00b7博格',
        'avatar': 'J',
        'style': style,
        'comment': '\n\n'.join(lines),
    }


def _marks(r1, mdd_1, mdd_all, vol, calmar_1):
    style = '周期思维 \u00b7 第二层思维 \u00b7 风险意识'
    lines = []

    lines.append(
        '霍华德·马克斯是《投资最重要的事》的作者，他强调周期思维和风险意识。'
        '他的"第二层思维"要求投资者比别人想得更深入、更全面。'
    )

    if r1 is not None:
        if r1 > 0.50:
            lines.append(
                '近 1 年涨幅约 %.0f%%。马克斯会提醒：市场大幅上涨后，'
                '乐观情绪往往已经反映在价格中。第二层思维要求我们思考：'
                '"现在市场预期了什么？这个预期是否过于完美？"' % (r1 * 100)
            )
        elif r1 > 0.20:
            lines.append(
                '近 1 年涨幅 %.0f%%。马克斯认为：知道我们处于周期的什么位置，'
                '比预测下一步走向重要得多。牛市中上涨不异常，关键在于判断上涨是由基本面还是情绪驱动。' % (r1 * 100)
            )
        elif r1 < 0:
            lines.append(
                '近 1 年跌幅约 %.0f%%。马克斯指出：悲观情绪本身可能是机会的信号，'
                '但需要区分是"暂时的市场恐慌"还是"基本面的永久恶化"。第二层思维帮助我们做出这个区分。' % (abs(r1) * 100)
            )

    if mdd_1 is not None and abs(mdd_1) > 0.20:
        lines.append(
            '1 年内最大回撤 %.0f%%。马克斯常说：风险不是波动，风险是永久性损失的可能性。'
            '好的投资者不是能预测风险，而是对风险始终保持敬畏。' % (abs(mdd_1) * 100)
        )

    if mdd_all is not None:
        lines.append(
            '自成立最大回撤 %.0f%%。马克斯的核心洞察：金融市场的极端事件'
            '比正态分布预测的要频繁得多。了解历史最坏情况有助于做好心理准备。' % (abs(mdd_all) * 100)
        )

    if vol is not None and vol > 0.30:
        lines.append(
            '年化波动率 %.1f%%，较高。马克斯不把波动等同于风险，但他会问：'
            '"这个波动背后，是否有永久性损失的可能？"这才是风险的本质。' % (vol * 100)
        )

    if calmar_1 is not None:
        lines.append(
            'Calmar 比率 %.1f。马克斯的投资方法论：追求可重复的、'
            '经过风险调整的回报，而非仅仅高额的绝对收益。' % calmar_1
        )

    return {
        'master': '霍华德\u00b7马克斯',
        'avatar': 'H',
        'style': style,
        'comment': '\n\n'.join(lines),
    }
