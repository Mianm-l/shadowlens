"""
High-fidelity mock data representing typical enterprise Oracle tables.
Enables offline development, testing, and demo without live DB.
"""

MOCK_DATASET = {
    "CT_PURCHASE_ORDER": [
        {
            "ORDER_ID": "PO-2026-0901",
            "SUPPLIER_NAME": "海南绿丰农林果蔬发展有限公司",
            "CONTACT_PHONE": "13876543210",
            "TOTAL_AMOUNT": 158200.00,
            "ORDER_STATUS": 2, # 已审批生效
            "CREATE_TIME": "2026-09-01 09:30:00",
            "DEPT_NAME": "蔬菜保供物资采购部"
        },
        {
            "ORDER_ID": "PO-2026-0902",
            "SUPPLIER_NAME": "海口顺达冷链水产储运中心",
            "CONTACT_PHONE": "13907654321",
            "TOTAL_AMOUNT": 326000.50,
            "ORDER_STATUS": 2, # 已审批生效 (在入库单中存在金额不一致)
            "CREATE_TIME": "2026-09-03 14:15:00",
            "DEPT_NAME": "水产供应链事业部"
        },
        {
            "ORDER_ID": "PO-2026-0903",
            "SUPPLIER_NAME": "澄迈现代农业种苗育繁基地",
            "CONTACT_PHONE": "13700001122",
            "TOTAL_AMOUNT": 84500.00,
            "ORDER_STATUS": 2, # 已审批生效 (但在入库单中缺失！漏单对账发现)
            "CREATE_TIME": "2026-09-05 10:00:00",
            "DEPT_NAME": "农业种植中心"
        },
        {
            "ORDER_ID": "PO-2026-0904",
            "SUPPLIER_NAME": "三亚热带种质资源科创园",
            "CONTACT_PHONE": "18889998877",
            "TOTAL_AMOUNT": 45000.00,
            "ORDER_STATUS": 1, # 审批中
            "CREATE_TIME": "2026-09-08 16:20:00",
            "DEPT_NAME": "科研育种部"
        }
    ],

    "CT_RECEIVING_BILL": [
        {
            "RECEIVE_ID": "RCV-2026-0901",
            "REF_ORDER_ID": "PO-2026-0901",
            "ACTUAL_AMOUNT": 158200.00,
            "INSPECT_STATUS": 2, # 质检合格
            "WAREHOUSE_NAME": "海口秀英保供1号冷库",
            "RECEIVE_TIME": "2026-09-04 11:20:00"
        },
        {
            "RECEIVE_ID": "RCV-2026-0902",
            "REF_ORDER_ID": "PO-2026-0902",
            "ACTUAL_AMOUNT": 310000.00, # 金额不一致！(采购326000.50, 实收310000.00, 差额16000.50)
            "INSPECT_STATUS": 2, # 质检合格
            "WAREHOUSE_NAME": "美兰水产直调库",
            "RECEIVE_TIME": "2026-09-06 17:00:00"
        },
        {
            "RECEIVE_ID": "RCV-2026-0905",
            "REF_ORDER_ID": "PO-2026-0888",
            "ACTUAL_AMOUNT": 92000.00,
            "INSPECT_STATUS": 2, # 质检合格但未生成财务凭证！
            "WAREHOUSE_NAME": "江东新区调配总仓",
            "RECEIVE_TIME": "2026-09-07 09:10:00"
        }
    ],

    "NC_PAY_VOUCHER": [
        {
            "VOUCHER_ID": "VCH-2026-09-001",
            "SOURCE_BIZ_ID": "RCV-2026-0901",
            "VOUCHER_CODE": "记-20260901-008",
            "VOUCHER_AMOUNT": 158200.00,
            "POST_STATUS": 1, # 已记账
            "POST_DATE": "2026-09-05"
        },
        {
            "VOUCHER_ID": "VCH-2026-09-002",
            "SOURCE_BIZ_ID": "RCV-2026-0902",
            "VOUCHER_CODE": "记-20260906-015",
            "VOUCHER_AMOUNT": 310000.00,
            "POST_STATUS": 0, # 未过账 (长期滞留)
            "POST_DATE": "2026-09-08"
        }
    ],

    "OA_COL_SUMMARY": [
        {
            "ID": 8801001,
            "SUBJECT": "关于江东保供综合体三期施工合同补充协议审批",
            "START_MEMBER_NAME": "张明远",
            "START_DATE": "2026-10-12 09:00:00",
            "FINISH_DATE": None,
            "STATE": 1 # 流转中
        },
        {
            "ID": 8801002,
            "SUBJECT": "2026年度第四季度农药与冷链温控设备集中采购请示",
            "START_MEMBER_NAME": "李秀兰",
            "START_DATE": "2026-10-14 14:30:00",
            "FINISH_DATE": None,
            "STATE": 1 # 流转中
        },
        {
            "ID": 8801003,
            "SUBJECT": "财务部三季度预决算差异对账说明公文",
            "START_MEMBER_NAME": "王建国",
            "START_DATE": "2026-10-18 10:00:00",
            "FINISH_DATE": None,
            "STATE": 1 # 流转中
        }
    ],

    "OA_COL_AFFAIR": [
        {
            "ID": 9902001,
            "OBJECT_ID": 8801001,
            "MEMBER_NAME": "陈建国(法务合规部)",
            "MEMBER_PHONE": "13612345678",
            "STATE": 1, # 待办/未读
            "RECEIVE_TIME": "2026-10-12 10:30:00", # 至今已超过 168 小时！严重卡点！
            "COMPLETE_TIME": None
        },
        {
            "ID": 9902002,
            "OBJECT_ID": 8801002,
            "MEMBER_NAME": "林德海(副总经理审批)",
            "MEMBER_PHONE": "13988776655",
            "STATE": 2, # 在办/已读
            "RECEIVE_TIME": "2026-10-15 08:20:00", # 超过 96 小时卡点
            "COMPLETE_TIME": None
        },
        {
            "ID": 9902003,
            "OBJECT_ID": 8801003,
            "MEMBER_NAME": "刘晓敏(财务总监)",
            "MEMBER_PHONE": "13766554433",
            "STATE": 1,
            "RECEIVE_TIME": "2026-10-18 11:00:00", # 正常流转中
            "COMPLETE_TIME": None
        }
    ]
}
