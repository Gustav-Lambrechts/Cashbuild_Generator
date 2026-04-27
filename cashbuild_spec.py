from __future__ import annotations

from config import template_standards

STANDARDS = template_standards()

cashbuild_spec = {
    "meta": {
        "name": "Cashbuild Building Specifications",
        "version": "March 2024",
        "revision": "i4.0",
        "source": "TSD 00520 CB Building Specs March 2024"
    },

    "building_program": {
        "required_major_areas": [
            "trading_floor_area",
            "offices_and_ablutions_area",
            "yard_area",
            "parking_area",
            "off_loading_area"
        ],
        "notes": [
            "These 5 areas must be represented in the overall site/building logic."
        ]
    },

    "global_rules": {
        "structure": {
            "trading_floor_clear_span_required": True,
            "trading_floor_min_internal_area_m2": STANDARDS["trading_minimum_area_m2"],
            "trading_floor_target_internal_area_m2": STANDARDS["trading_ideal_area_m2"],
            "trading_floor_preferred_dimensions_m": STANDARDS["trading_preferred_dimensions_m"],
            "trading_floor_compact_dimensions_m": STANDARDS["trading_compact_dimensions_m"],
            "trading_floor_lowest_truss_height_m": 6.0
        },

        "admin_block": {
            "target_area_m2": STANDARDS["admin_target_area_m2"],
            "preferred_depth_range_m": STANDARDS["admin_preferred_depth_range_m"],
            "allowed_configurations": ["single_storey", "double_storey"],
            "must_be_attached_to_main_building_side": True,
            "internal_access_required": True,
            "internal_access_spaces": [
                "cash_office",
                "goods_receiving",
                "canteen",
                "male_toilets_and_change_room",
                "female_toilets_and_change_room"
            ]
        },

        "yard": {
            "required": True,
            "minimum_area_m2": STANDARDS["yard_minimum_area_m2"],
            "must_be_fenced": True,
            "minimum_fence_height_m": 2.4,
            "bin_area_min_m2": 17,
            "generator_plinth_required": True,
            "generator_plinth_size_m": [2.5, 2.5],
            "generator_clear_space_mm": [500, 800],
            "sliding_gate_required": True,
            "yard_sliding_gate_size_m": [5.5, 2.0]
        },

        "off_loading": {
            "required": True,
            "minimum_area_m2": STANDARDS["offloading_minimum_area_m2"],
            "must_connect_to_yard": True,
            "must_connect_to_roadway": True,
            "sliding_gate_size_m": [7.0, 2.4],
            "truck_access_required": True
        },

        "parking": {
            "required": True,
            "must_include_disabled_bay_near_entrance": True
        }
    },

    "spaces": [
        {
            "name": "trading_area",
            "category": "primary",
            "group": "customer",
            "required": True,
            "target_area_m2": STANDARDS["trading_ideal_area_m2"],
            "min_area_m2": STANDARDS["trading_minimum_area_m2"],
            "preferred_width_depth_m": STANDARDS["trading_preferred_dimensions_m"],
            "compact_width_depth_m": STANDARDS["trading_compact_dimensions_m"],
            "aspect_ratio_range": [0.75, 1.5],
            "must_touch": ["front_customer_edge"],
            "prefer_touch": ["front_loading_edge"],
            "adjacent_to": [
                "goods_receiving",
                "cash_office",
                "passage",
                "front_customer_loading_zone"
            ],
            "must_not_have": ["internal_columns_protruding", "windows"],
            "contains": [
                "entrance_door",
                "sliding_exit_door_1",
                "sliding_exit_door_2",
                "roller_shutter_4x4_front",
                "roller_shutter_4x4_back",
                "roller_shutter_2_4x2_4_exit_1",
                "roller_shutter_2_4x2_4_exit_2",
                "roller_shutter_1_8x2_4"
            ]
        },

        {
            "name": "goods_receiving",
            "category": "primary_support",
            "group": "service",
            "required": True,
            "target_area_m2": None,
            "min_area_m2": None,
            "must_touch": ["service_edge_or_yard_edge"],
            "adjacent_to": [
                "trading_area",
                "cash_office",
                "yard_area",
                "off_loading_area",
                "passage"
            ],
            "prefer_touch": ["yard_area", "off_loading_area"],
            "notes": [
                "If goods receiving is not inside yard or dedicated off-loading yard, provide external roller shutter.",
                "If inside yard and shutter inaccessible without entering yard, roller shutter may be omitted."
            ]
        },

        {
            "name": "cash_office",
            "category": "primary_support",
            "group": "admin",
            "required": True,
            "target_area_m2": None,
            "min_area_m2": None,
            "must_touch": ["admin_block"],
            "adjacent_to": [
                "goods_receiving",
                "passage",
                "trading_area"
            ],
            "special_rules": [
                "Must accommodate strong_room",
                "Should be internally connected"
            ]
        },

        {
            "name": "strong_room",
            "category": "subspace",
            "group": "security",
            "required": True,
            "parent": "cash_office",
            "adjacent_to": ["cash_office"],
            "special_rules": [
                "Ballistic door required",
                "Security enclosure logic required"
            ]
        },

        {
            "name": "male_toilets_and_change_room",
            "category": "support",
            "group": "staff",
            "required": True,
            "parent_zone": "offices_and_ablutions_area",
            "must_touch": ["perimeter_preferred"],
            "adjacent_to": ["passage"],
            "prefer_near": ["female_toilets_and_change_room", "canteen"]
        },

        {
            "name": "female_toilets_and_change_room",
            "category": "support",
            "group": "staff",
            "required": True,
            "parent_zone": "offices_and_ablutions_area",
            "must_touch": ["perimeter_preferred"],
            "adjacent_to": ["passage"],
            "prefer_near": ["male_toilets_and_change_room", "canteen"]
        },

        {
            "name": "passage",
            "category": "circulation",
            "group": "staff",
            "required": True,
            "parent_zone": "offices_and_ablutions_area",
            "adjacent_to": [
                "trading_area",
                "goods_receiving",
                "cash_office",
                "male_toilets_and_change_room",
                "female_toilets_and_change_room",
                "canteen"
            ],
            "special_rules": [
                "Acts as admin/staff circulation spine"
            ]
        },

        {
            "name": "canteen",
            "category": "support",
            "group": "staff",
            "required": True,
            "parent_zone": "offices_and_ablutions_area",
            "must_touch": ["perimeter_preferred"],
            "adjacent_to": ["passage"],
            "prefer_near": [
                "male_toilets_and_change_room",
                "female_toilets_and_change_room"
            ]
        },

        {
            "name": "yard_area",
            "category": "site_service",
            "group": "external_service",
            "required": True,
            "min_area_m2": STANDARDS["yard_minimum_area_m2"],
            "must_touch": ["service_edge"],
            "adjacent_to": ["goods_receiving", "off_loading_area"],
            "contains": [
                "bin_area",
                "generator_plinth",
                "water_tank",
                "yard_sliding_gate"
            ]
        },

        {
            "name": "off_loading_area",
            "category": "site_service",
            "group": "external_service",
            "required": True,
            "min_area_m2": STANDARDS["offloading_minimum_area_m2"],
            "must_touch": ["roadway_edge", "yard_edge"],
            "adjacent_to": ["yard_area", "goods_receiving"],
            "special_rules": [
                "Must accommodate truck movement"
            ]
        },

        {
            "name": "parking_area",
            "category": "site_customer",
            "group": "external_customer",
            "required": True,
            "must_touch": ["front_customer_edge"],
            "adjacent_to": ["trading_area"],
            "contains": [
                "disabled_parking_bay",
                "front_loading_zone"
            ]
        }
    ],

    "door_and_opening_rules": {
        "trading_area": {
            "front_customer_entrance": {
                "type": "double_swing_glazed",
                "size_m": [1.626, 2.1],
                "opens_inward": True
            },
            "customer_exit_doors": [
                {
                    "type": "split_sliding_glazed",
                    "size_m": [2.4, 2.1]
                },
                {
                    "type": "split_sliding_glazed",
                    "size_m": [2.4, 2.1]
                }
            ],
            "roller_shutters": [
                {"size_m": [4.0, 4.0], "count": 2},
                {"size_m": [2.4, 2.4], "count": 2},
                {"size_m": [1.8, 2.4], "count": 1}
            ]
        },
        "goods_receiving": {
            "optional_external_roller_shutter": {
                "size_m": [1.4, 1.8],
                "conditional": True
            },
            "internal_door_to_trading": {
                "type": "solid_timber",
                "required": True
            }
        }
    },

    "layout_logic": {
        "top_level_partition_strategy": [
            "Create dominant trading rectangle first",
            "Attach offices_and_ablutions block to one side of main building",
            "Place goods_receiving at service side interface between trading and yard/off-loading",
            "Place yard and off-loading on service side",
            "Place parking and customer approach on front side"
        ],

        "admin_block_subdivision_strategy": [
            "Create passage spine first",
            "Attach cash_office to goods_receiving/trading relationship",
            "Place male and female change/ablution rooms off passage",
            "Place canteen off passage",
            "Prefer perimeter for canteen and ablution rooms"
        ],

        "service_cluster_strategy": [
            "Group goods_receiving, yard_area, and off_loading_area tightly",
            "Minimize travel distance from off-loading to goods_receiving",
            "Minimize travel distance from goods_receiving to trading floor"
        ],

        "customer_side_strategy": [
            "Front customer side should contain main entrance and customer parking interface",
            "Customer exits and loading apron should align with front roller shutters and exit doors",
            "Promo/cashier logic may later be overlaid inside trading area near entrance"
        ]
    },

    "known_constraints_for_generator": {
        "trading_area_no_windows": True,
        "trading_area_skylights_allowed_except_over_pos": True,
        "front_canopy_required": True,
        "front_canopy_height_m": 3.6,
        "front_canopy_width_m": 2.4,
        "roller_shutter_canopy_height_m": 4.6,
        "roller_shutter_canopy_width_m": 4.6,
        "front_loading_hardstand_min_m2": 50
    },

    "unknowns_to_confirm": [
        "Exact target area for goods_receiving",
        "Exact target area for cash_office excluding strong room",
        "Exact area allocations for male and female change rooms",
        "Exact canteen area",
        "Preferred single-storey vs double-storey admin default by prototype",
        "Exact passage width standard",
        "Exact default site depth and width variants",
        "Exact internal position of cashier/POS relative to entrance"
    ]
}
