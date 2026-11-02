"""
SIH26002 — Management command to seed the Guwahati–Shillong–Silchar
NER multimodal corridor.

Includes:
- Road network: NH-6, NH-27
- Rail links: Guwahati-Lumding-Badarpur-Silchar
- Inland waterways:
  - NW-2 Brahmaputra/Pandu
  - NW-16 Barak/Silchar

NOTE:
All economic rates, water levels, and hazard ratings are representative
DEMO data for simulation.
"""

from django.contrib.gis.geos import LineString, Point
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.transport_graph.models import (
    EdgeStatus,
    NodeType,
    TransportEdge,
    TransportMode,
    TransportNode,
)
from apps.transport_graph.validation import TransportGraphValidator


class Command(BaseCommand):
    help = (
        "Seed the Guwahati–Shillong–Silchar multimodal "
        "transport graph for NER logistics (DEMO DATA)."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            "Seeding Guwahati–Shillong–Silchar "
            "multimodal transport graph (DEMO DATA)..."
        )

        with transaction.atomic():

            # ============================================================
            # 0. CLEAN PREVIOUS DEMO EDGES
            # ============================================================
            #
            # This makes the seed command idempotent.
            # Only edges created by this demo seed are removed.
            # Production/imported edges are NOT touched.
            #
            TransportEdge.objects.filter(
                data_source="seed_ner_corridor_demo"
            ).delete()

            # ============================================================
            # 1. DEFINE NODES
            # ============================================================

            nodes_data = [

                # --------------------------------------------------------
                # Guwahati & Kamrup Metro (Assam)
                # --------------------------------------------------------

                (
                    "Guwahati Multimodal Logistics Park",
                    91.5850,
                    26.1150,
                    54.0,
                    "Assam",
                    "Kamrup Metro",
                    NodeType.MULTIMODAL_HUB,
                    "GAU-MMLP",
                ),

                (
                    "Pandu Port Inland Waterway Terminal (NW-2)",
                    91.6833,
                    26.1550,
                    48.0,
                    "Assam",
                    "Kamrup Metro",
                    NodeType.WATERWAY_TERMINAL,
                    "GAU-PANDU",
                ),

                (
                    "Guwahati Railway Freight Yard",
                    91.7539,
                    26.1824,
                    55.0,
                    "Assam",
                    "Kamrup Metro",
                    NodeType.RAIL_YARD,
                    "GAU-RLY",
                ),

                (
                    "Khanapara Transport Junction",
                    91.8210,
                    26.1260,
                    62.0,
                    "Assam",
                    "Kamrup Metro",
                    NodeType.ROAD_INTERSECTION,
                    "GAU-KHAN",
                ),

                (
                    "Jorabat Border Junction",
                    91.8680,
                    26.0960,
                    95.0,
                    "Assam",
                    "Kamrup Metro",
                    NodeType.CHECKPOST,
                    "AS-JORABAT",
                ),

                # --------------------------------------------------------
                # NH-6 Ri-Bhoi Corridor (Meghalaya)
                # --------------------------------------------------------

                (
                    "Byrnihat Industrial Node",
                    91.8850,
                    26.0550,
                    140.0,
                    "Meghalaya",
                    "Ri-Bhoi",
                    NodeType.LOGISTICS_HUB,
                    "ML-BYRNI",
                ),

                (
                    "Nongpoh Freight Rest & Fuel Hub",
                    91.8790,
                    25.9030,
                    550.0,
                    "Meghalaya",
                    "Ri-Bhoi",
                    NodeType.ROAD_INTERSECTION,
                    "ML-NONGPOH",
                ),

                (
                    "Umsning Expressway Junction",
                    91.8980,
                    25.7520,
                    820.0,
                    "Meghalaya",
                    "Ri-Bhoi",
                    NodeType.ROAD_INTERSECTION,
                    "ML-UMSNING",
                ),

                (
                    "Umiam Barapani Lake Junction",
                    91.9050,
                    25.6600,
                    1020.0,
                    "Meghalaya",
                    "Ri-Bhoi",
                    NodeType.ROAD_INTERSECTION,
                    "ML-UMIAM",
                ),

                # --------------------------------------------------------
                # Shillong & East Khasi Hills
                # --------------------------------------------------------

                (
                    "Mawlai Bypass Junction",
                    91.8890,
                    25.6020,
                    1450.0,
                    "Meghalaya",
                    "East Khasi Hills",
                    NodeType.ROAD_INTERSECTION,
                    "ML-MAWLAI",
                ),

                (
                    "Shillong Central Logistics Hub",
                    91.8830,
                    25.5788,
                    1525.0,
                    "Meghalaya",
                    "East Khasi Hills",
                    NodeType.LOGISTICS_HUB,
                    "ML-SHILLONG",
                ),

                (
                    "Laitkor Peak Junction",
                    91.9120,
                    25.5450,
                    1800.0,
                    "Meghalaya",
                    "East Khasi Hills",
                    NodeType.ROAD_INTERSECTION,
                    "ML-LAITKOR",
                ),

                # --------------------------------------------------------
                # Jaintia Hills Corridor
                # --------------------------------------------------------

                (
                    "Jowai Freight Terminal",
                    92.2150,
                    25.4520,
                    1380.0,
                    "Meghalaya",
                    "West Jaintia Hills",
                    NodeType.LOGISTICS_HUB,
                    "ML-JOWAI",
                ),

                (
                    "Lad Rymbai Mining Logistics Node",
                    92.3480,
                    25.3210,
                    1150.0,
                    "Meghalaya",
                    "East Jaintia Hills",
                    NodeType.WAREHOUSE,
                    "ML-LADRYMBAI",
                ),

                (
                    "Khliehriat Transport Depot",
                    92.3680,
                    25.3520,
                    1200.0,
                    "Meghalaya",
                    "East Jaintia Hills",
                    NodeType.ROAD_INTERSECTION,
                    "ML-KHLIEH",
                ),

                (
                    "Sonapur Landslide Zone & Tunnel",
                    92.4180,
                    25.1050,
                    320.0,
                    "Meghalaya",
                    "East Jaintia Hills",
                    NodeType.ROAD_INTERSECTION,
                    "ML-SONAPUR",
                ),

                (
                    "Malidor Inter-State Border Checkpost",
                    92.4650,
                    24.9980,
                    110.0,
                    "Meghalaya",
                    "East Jaintia Hills",
                    NodeType.CHECKPOST,
                    "ML-MALIDOR",
                ),

                # --------------------------------------------------------
                # Barak Valley Gateway
                # --------------------------------------------------------

                (
                    "Gumrah Highway Junction",
                    92.4850,
                    24.9650,
                    50.0,
                    "Assam",
                    "Cachar",
                    NodeType.ROAD_INTERSECTION,
                    "AS-GUMRAH",
                ),

                (
                    "Kalain Junction",
                    92.5680,
                    24.9750,
                    42.0,
                    "Assam",
                    "Cachar",
                    NodeType.ROAD_INTERSECTION,
                    "AS-KALAIN",
                ),

                (
                    "Badarpur Multimodal Rail & Freight Hub",
                    92.6020,
                    24.9010,
                    35.0,
                    "Assam",
                    "Karimganj",
                    NodeType.MULTIMODAL_HUB,
                    "AS-BADARPUR",
                ),

                (
                    "Panchgram Industrial Node",
                    92.6500,
                    24.8750,
                    32.0,
                    "Assam",
                    "Hailakandi",
                    NodeType.WAREHOUSE,
                    "AS-PANCHGRAM",
                ),

                (
                    "Silchar Central Goods Logistics Yard",
                    92.7925,
                    24.8333,
                    25.0,
                    "Assam",
                    "Cachar",
                    NodeType.MULTIMODAL_HUB,
                    "AS-SILCHAR-HUB",
                ),

                (
                    "Silchar Sadarghat River Jetty (NW-16)",
                    92.8050,
                    24.8250,
                    22.0,
                    "Assam",
                    "Cachar",
                    NodeType.RIVER_JETTY,
                    "AS-SILCHAR-JETTY",
                ),

                (
                    "Fulertal Inland Waterway Terminal (NW-16)",
                    93.0320,
                    24.7850,
                    28.0,
                    "Assam",
                    "Cachar",
                    NodeType.WATERWAY_TERMINAL,
                    "AS-FULERTAL",
                ),

                # --------------------------------------------------------
                # Hill Rail Alternative
                # --------------------------------------------------------

                (
                    "Lumding Rail Junction Hub",
                    93.1700,
                    25.7500,
                    125.0,
                    "Assam",
                    "Hojai",
                    NodeType.RAIL_YARD,
                    "AS-LUMDING",
                ),

                (
                    "New Haflong Hill Railway Station",
                    93.0180,
                    25.1750,
                    513.0,
                    "Assam",
                    "Dima Hasao",
                    NodeType.RAIL_SIDING,
                    "AS-HAFLONG",
                ),
            ]

            node_objs = {}

            for (
                name,
                lon,
                lat,
                elev,
                state,
                dist,
                n_type,
                code,
            ) in nodes_data:

                node, _ = TransportNode.objects.update_or_create(
                    short_code=code,
                    defaults={
                        "name": name,
                        "geometry": Point(lon, lat, srid=4326),
                        "elevation_m": elev,
                        "state": state,
                        "district": dist,
                        "node_type": n_type,
                        "is_active": True,
                        "data_source": "seed_ner_corridor_demo",
                    },
                )

                node_objs[code] = node

            self.stdout.write(
                f"Created/updated {len(node_objs)} transport nodes."
            )

            # ============================================================
            # 2. EDGE HELPER
            # ============================================================

            def add_edge(
                src_code,
                tgt_code,
                mode,
                dist_km,
                time_min,
                cost_inr,
                hazard=0.0,
                status=EdgeStatus.OPEN,
                road_name="",
                bidirectional=True,
                transfer_time=None,
                transfer_cost=None,
                capacity_kg=25000.0,
                water_level=None,
                min_depth=None,
                draft_req=None,
            ):
                u = node_objs[src_code]
                v = node_objs[tgt_code]

                geom_fwd = LineString(
                    [u.geometry, v.geometry],
                    srid=4326,
                )

                geom_rev = LineString(
                    [v.geometry, u.geometry],
                    srid=4326,
                )

                defaults_dict = {
                    "distance_m": dist_km * 1000.0,
                    "base_transit_time_min": time_min,
                    "cost_inr": cost_inr,
                    "hazard_score": hazard,
                    "status": status,
                    "capacity_kg": capacity_kg,
                    "is_available": (
                        status
                        not in [
                            EdgeStatus.BLOCKED,
                            EdgeStatus.CRITICAL,
                        ]
                    ),
                    "road_name": road_name,
                    "geometry": geom_fwd,
                    "transfer_time_min": transfer_time,
                    "transfer_cost_inr": transfer_cost,
                    "water_level_m": water_level,
                    "min_required_depth_m": min_depth,
                    "draft_requirement_m": draft_req,
                    "data_source": "seed_ner_corridor_demo",
                }

                TransportEdge.objects.update_or_create(
                    source_node=u,
                    target_node=v,
                    mode=mode,
                    defaults=defaults_dict,
                )

                if bidirectional:
                    rev_dict = defaults_dict.copy()
                    rev_dict["geometry"] = geom_rev

                    TransportEdge.objects.update_or_create(
                        source_node=v,
                        target_node=u,
                        mode=mode,
                        defaults=rev_dict,
                    )

            # ============================================================
            # 3. INTERMODAL TRANSFERS - GUWAHATI
            # ============================================================

            add_edge(
                "GAU-MMLP",
                "GAU-PANDU",
                TransportMode.TRANSFER,
                8.0,
                30.0,
                500.0,
                road_name="Pandu Port Multimodal Link",
                transfer_time=45.0,
                transfer_cost=1200.0,
            )

            add_edge(
                "GAU-MMLP",
                "GAU-RLY",
                TransportMode.TRANSFER,
                12.0,
                35.0,
                450.0,
                road_name="Guwahati Rail Yard Transfer",
                transfer_time=40.0,
                transfer_cost=900.0,
            )

            # IMPORTANT:
            # Railway Yard cannot originate/terminate ROAD traffic
            # according to the graph validator.
            #
            # Therefore this connection is represented as TRANSFER.
            add_edge(
                "GAU-RLY",
                "GAU-KHAN",
                TransportMode.TRANSFER,
                11.0,
                30.0,
                400.0,
                road_name="Rail Yard-Khanapara Transfer",
                transfer_time=20.0,
                transfer_cost=400.0,
                capacity_kg=15000.0,
            )

            # ============================================================
            # 4. NH-6 HIGHWAY: GUWAHATI -> SHILLONG
            # ============================================================

            add_edge(
                "GAU-KHAN",
                "AS-JORABAT",
                TransportMode.ROAD,
                6.5,
                15.0,
                250.0,
                hazard=0.08,
                road_name="NH-6 Khanapara-Jorabat",
                capacity_kg=35000.0,
            )

            add_edge(
                "AS-JORABAT",
                "ML-BYRNI",
                TransportMode.ROAD,
                9.2,
                20.0,
                350.0,
                hazard=0.12,
                road_name="NH-6 Jorabat-Byrnihat",
                capacity_kg=35000.0,
            )

            add_edge(
                "ML-BYRNI",
                "ML-NONGPOH",
                TransportMode.ROAD,
                32.0,
                50.0,
                1200.0,
                hazard=0.18,
                road_name="NH-6 Byrnihat-Nongpoh 4-Lane",
                capacity_kg=35000.0,
            )

            add_edge(
                "ML-NONGPOH",
                "ML-UMSNING",
                TransportMode.ROAD,
                21.0,
                35.0,
                800.0,
                hazard=0.20,
                road_name="NH-6 Nongpoh-Umsning Expressway",
                capacity_kg=35000.0,
            )

            add_edge(
                "ML-UMSNING",
                "ML-UMIAM",
                TransportMode.ROAD,
                14.0,
                25.0,
                550.0,
                hazard=0.15,
                road_name="NH-6 Umsning-Umiam Expressway",
                capacity_kg=35000.0,
            )

            add_edge(
                "ML-UMIAM",
                "ML-MAWLAI",
                TransportMode.ROAD,
                10.0,
                20.0,
                400.0,
                hazard=0.18,
                road_name="NH-6 Umiam-Mawlai",
                capacity_kg=25000.0,
            )

            add_edge(
                "ML-MAWLAI",
                "ML-SHILLONG",
                TransportMode.ROAD,
                5.0,
                15.0,
                200.0,
                hazard=0.08,
                road_name="Shillong Urban Arterial",
                capacity_kg=15000.0,
            )

            # ============================================================
            # 5. NH-6: SHILLONG -> JOWAI -> SILCHAR
            # ============================================================

            add_edge(
                "ML-SHILLONG",
                "ML-LAITKOR",
                TransportMode.ROAD,
                7.5,
                20.0,
                300.0,
                hazard=0.15,
                road_name="Shillong-Laitkor Peak Road",
                capacity_kg=20000.0,
            )

            add_edge(
                "ML-LAITKOR",
                "ML-JOWAI",
                TransportMode.ROAD,
                58.0,
                110.0,
                2400.0,
                hazard=0.25,
                road_name="NH-6 Shillong-Jowai Highway",
                capacity_kg=25000.0,
            )

            add_edge(
                "ML-JOWAI",
                "ML-LADRYMBAI",
                TransportMode.ROAD,
                35.0,
                75.0,
                1500.0,
                hazard=0.40,
                road_name="NH-6 Jowai-Ladrymbai Mining Belt",
                capacity_kg=35000.0,
            )

            add_edge(
                "ML-LADRYMBAI",
                "ML-KHLIEH",
                TransportMode.ROAD,
                8.0,
                18.0,
                350.0,
                hazard=0.35,
                road_name="NH-6 Ladrymbai-Khliehriat",
                capacity_kg=35000.0,
            )

            # Sonapur Tunnel area:
            # High hazard zone during monsoon.
            add_edge(
                "ML-KHLIEH",
                "ML-SONAPUR",
                TransportMode.ROAD,
                28.0,
                70.0,
                1400.0,
                hazard=0.75,
                road_name="NH-6 Khliehriat-Sonapur Landslide Zone",
                capacity_kg=25000.0,
            )

            add_edge(
                "ML-SONAPUR",
                "ML-MALIDOR",
                TransportMode.ROAD,
                18.0,
                45.0,
                900.0,
                hazard=0.55,
                road_name="NH-6 Sonapur-Malidor Pass",
                capacity_kg=25000.0,
            )

            # ============================================================
            # 6. ASSAM VALLEY -> SILCHAR
            # ============================================================

            add_edge(
                "ML-MALIDOR",
                "AS-GUMRAH",
                TransportMode.ROAD,
                8.0,
                20.0,
                350.0,
                hazard=0.18,
                road_name="NH-6 Malidor-Gumrah Border Road",
                capacity_kg=30000.0,
            )

            add_edge(
                "AS-GUMRAH",
                "AS-KALAIN",
                TransportMode.ROAD,
                12.0,
                25.0,
                480.0,
                hazard=0.12,
                road_name="NH-6 Gumrah-Kalain",
                capacity_kg=30000.0,
            )

            add_edge(
                "AS-KALAIN",
                "AS-BADARPUR",
                TransportMode.ROAD,
                16.0,
                32.0,
                650.0,
                hazard=0.12,
                road_name="NH-6 Kalain-Badarpur",
                capacity_kg=30000.0,
            )

            add_edge(
                "AS-BADARPUR",
                "AS-PANCHGRAM",
                TransportMode.ROAD,
                11.0,
                25.0,
                450.0,
                hazard=0.08,
                road_name="Badarpur-Panchgram Road",
                capacity_kg=25000.0,
            )

            add_edge(
                "AS-PANCHGRAM",
                "AS-SILCHAR-HUB",
                TransportMode.ROAD,
                22.0,
                45.0,
                900.0,
                hazard=0.08,
                road_name="NH-37 Panchgram-Silchar City",
                capacity_kg=35000.0,
            )

            # ============================================================
            # 7. SILCHAR TRANSFER + NW-16 WATERWAY
            # ============================================================

            add_edge(
                "AS-SILCHAR-HUB",
                "AS-SILCHAR-JETTY",
                TransportMode.TRANSFER,
                3.5,
                15.0,
                200.0,
                road_name="Silchar Sadarghat Jetty Link",
                transfer_time=30.0,
                transfer_cost=800.0,
            )

            add_edge(
                "AS-SILCHAR-JETTY",
                "AS-FULERTAL",
                TransportMode.WATER,
                38.0,
                180.0,
                850.0,
                hazard=0.05,
                road_name="NW-16 Barak River Inland Navigation",
                water_level=2.8,
                min_depth=1.8,
                draft_req=1.5,
                capacity_kg=80000.0,
            )

            # ============================================================
            # 8. ALTERNATIVE MULTIMODAL RAIL CORRIDOR
            # ============================================================

            add_edge(
                "GAU-RLY",
                "AS-LUMDING",
                TransportMode.RAIL,
                180.0,
                210.0,
                2200.0,
                hazard=0.05,
                road_name="North East Frontier Railway Mainline",
                capacity_kg=120000.0,
            )

            add_edge(
                "AS-LUMDING",
                "AS-HAFLONG",
                TransportMode.RAIL,
                98.0,
                160.0,
                1400.0,
                hazard=0.30,
                road_name="Dima Hasao Hill Section Rail (NFR)",
                capacity_kg=90000.0,
            )

            add_edge(
                "AS-HAFLONG",
                "AS-BADARPUR",
                TransportMode.RAIL,
                72.0,
                120.0,
                1100.0,
                hazard=0.20,
                road_name="Haflong-Badarpur Rail Descent",
                capacity_kg=90000.0,
            )

            add_edge(
                "AS-BADARPUR",
                "AS-SILCHAR-HUB",
                TransportMode.RAIL,
                30.0,
                45.0,
                400.0,
                hazard=0.05,
                road_name="Badarpur-Silchar Broad Gauge Branch",
                capacity_kg=90000.0,
            )

            # ============================================================
            # 9. VALIDATE SEEDED GRAPH
            # ============================================================

            edge_count = TransportEdge.objects.filter(
                data_source="seed_ner_corridor_demo"
            ).count()

            validator = TransportGraphValidator()
            validation_result = validator.validate_full_graph()

            if not validation_result.is_valid:
                self.stdout.write(
                    self.style.ERROR(
                        "Seeded graph validation failed with "
                        f"{len(validation_result.errors)} errors: "
                        f"{validation_result.errors}"
                    )
                )

                # IMPORTANT:
                # Raise an exception so transaction.atomic() rolls back.
                raise RuntimeError(
                    "Transport graph validation failed. "
                    "Demo graph was rolled back."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully seeded multimodal graph with "
                    f"{len(node_objs)} nodes and {edge_count} edges "
                    "(Validation PASSED with 0 errors)!"
                )
            )