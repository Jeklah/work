from receiver_mappings import SingleMapping


connections_single = {
    SingleMapping.VID_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fe4657fd-5dff-3c24-947e-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.20.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-0-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 96\r\nc=IN IP4 239.4.20.1/64\r\na=source-filter: incl IN IP4 239.4.20.1 192.168.10.4\r\na=rtpmap:96 raw/90000\r\na=fmtp:96 sampling=YCbCr-4:2:2; width=1920; height=1080; exactframerate=25; depth=10; TCS=SDR; colorimetry=BT709; PM=2110GPM; SSN=ST2110-20:2017; TP=2110TPN; \r\na=mediaclk:direct=0\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.VID_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fe4657fd-5dff-3c24-947e-40a36ba03fb2",
        "transport_params": [

            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.20.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-0-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 96\r\nc=IN IP4 239.4.20.2/64\r\na=source-filter: incl IN IP4 239.4.20.2 192.168.10.4\r\na=rtpmap:96 raw/90000\r\na=fmtp:96 sampling=YCbCr-4:2:2; width=1920; height=1080; exactframerate=25; depth=10; TCS=SDR; colorimetry=BT709; PM=2110GPM; SSN=ST2110-20:2017; TP=2110TPN; \r\na=mediaclk:direct=0\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD1_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fffbba85-fbd2-47b3-9f3f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.30.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-1-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.30.1/64\r\na=source-filter: incl IN IP4 239.4.30.1 192.168.10.4\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD1_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fffbba85-fbd2-47b3-9f3f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.30.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-1-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.30.2/64\r\na=source-filter: incl IN IP4 239.4.30.2 192.168.10.4\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD2_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "dfff1d0d-77bf-1341-a9ff-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.31.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-2-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.31.1/64\r\na=source-filter: incl IN IP4 239.4.31.1 192.168.10.4\r\na=rtpmap:97 AM824/48000/16\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD2_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "dfff1d0d-77bf-1341-a9ff-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.31.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-2-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.31.2/64\r\na=source-filter: incl IN IP4 239.4.31.2 192.168.10.4\r\na=rtpmap:97 AM824/48000/16\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD3_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "647f7f95-27eb-2ecf-a4bf-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.30.3",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-3-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.30.3/64\r\na=source-filter: incl IN IP4 239.4.30.3 192.168.0.1\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD3_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "647f7f95-27eb-2ecf-a4bf-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.30.4",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-3-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.30.4/64\r\na=source-filter: incl IN IP4 239.4.30.4 192.168.10.4\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD4_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "35fbe21d-bdff-3a5e-8f7f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.31.3",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-4-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.31.3/64\r\na=source-filter: incl IN IP4 239.4.31.3 192.168.0.1\r\na=rtpmap:97 AM824/48000/6\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD4_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "35fbe21d-bdff-3a5e-8f7f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.31.4",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-4-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.4.31.4/64\r\na=source-filter: incl IN IP4 239.4.31.4 192.168.0.1\r\na=rtpmap:97 AM824/48000/6\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.ANC_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "49f7cec5-fbb8-3425-9541-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.40.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-9-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 100\r\nc=IN IP4 239.4.40.1/64\r\na=source-filter: incl IN IP4 239.4.40.1 192.168.10.4\r\na=rtpmap:100 smpte291/90000\r\na=fmtp:100 VPID_Code=133; \r\na=mediaclk:direct=0 rate=90000\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.ANC_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "49f7cec5-fbb8-3425-9541-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.4.40.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-9-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 100\r\nc=IN IP4 239.4.40.2/64\r\na=source-filter: incl IN IP4 239.4.40.2 192.168.10.4\r\na=rtpmap:100 smpte291/90000\r\na=fmtp:100 VPID_Code=133; \r\na=mediaclk:direct=0 rate=90000\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    }

}

non_matching_connections_single = {
    SingleMapping.VID_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fe4657fd-5dff-3c24-947e-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.20.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-0-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 96\r\nc=IN IP4 239.5.20.1/64\r\na=source-filter: incl IN IP4 239.5.20.1 192.168.10.4\r\na=rtpmap:96 raw/90000\r\na=fmtp:96 sampling=YCbCr-4:2:2; width=1920; height=1080; exactframerate=25; depth=10; TCS=SDR; colorimetry=BT709; PM=2110GPM; SSN=ST2110-20:2017; TP=2110TPN; \r\na=mediaclk:direct=0\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.VID_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fe4657fd-5dff-3c24-947e-40a36ba03fb2",
        "transport_params": [

            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.20.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-0-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 96\r\nc=IN IP4 239.5.20.2/64\r\na=source-filter: incl IN IP4 239.5.20.2 192.168.10.4\r\na=rtpmap:96 raw/90000\r\na=fmtp:96 sampling=YCbCr-4:2:2; width=1920; height=1080; exactframerate=25; depth=10; TCS=SDR; colorimetry=BT709; PM=2110GPM; SSN=ST2110-20:2017; TP=2110TPN; \r\na=mediaclk:direct=0\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD1_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fffbba85-fbd2-47b3-9f3f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.30.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-1-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.30.1/64\r\na=source-filter: incl IN IP4 239.5.30.1 192.168.10.4\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD1_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "fffbba85-fbd2-47b3-9f3f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.30.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-1-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.30.2/64\r\na=source-filter: incl IN IP4 239.5.30.2 192.168.10.4\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD2_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "dfff1d0d-77bf-1341-a9ff-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.31.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-2-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.31.1/64\r\na=source-filter: incl IN IP4 239.5.31.1 192.168.10.4\r\na=rtpmap:97 AM824/48000/16\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD2_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "dfff1d0d-77bf-1341-a9ff-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.31.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-2-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.31.2/64\r\na=source-filter: incl IN IP4 239.5.31.2 192.168.10.4\r\na=rtpmap:97 AM824/48000/16\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD3_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "647f7f95-27eb-2ecf-a4bf-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.30.3",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-3-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.30.3/64\r\na=source-filter: incl IN IP4 239.5.30.3 192.168.0.1\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD3_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "647f7f95-27eb-2ecf-a4bf-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.30.4",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-3-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.30.4/64\r\na=source-filter: incl IN IP4 239.5.30.4 192.168.10.4\r\na=rtpmap:97 L24/48000/8\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:6\r\na=ptime:0.125\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD4_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "35fbe21d-bdff-3a5e-8f7f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.31.3",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-4-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.31.3/64\r\na=source-filter: incl IN IP4 239.5.31.3 192.168.0.1\r\na=rtpmap:97 AM824/48000/6\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.AUD4_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "35fbe21d-bdff-3a5e-8f7f-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.31.4",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-4-0\r\nt=0 0\r\nm=audio 20000 RTP/AVP 97\r\nc=IN IP4 239.5.31.4/64\r\na=source-filter: incl IN IP4 239.5.31.4 192.168.0.1\r\na=rtpmap:97 AM824/48000/6\r\na=mediaclk:direct=0 rate=48000\r\na=framecount:48\r\na=ptime:1\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.ANC_1: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "49f7cec5-fbb8-3425-9541-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.40.1",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-9-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 100\r\nc=IN IP4 239.5.40.1/64\r\na=source-filter: incl IN IP4 239.5.40.1 192.168.10.4\r\na=rtpmap:100 smpte291/90000\r\na=fmtp:100 VPID_Code=133; \r\na=mediaclk:direct=0 rate=90000\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    },

    SingleMapping.ANC_2: {
        "master_enable": True,
        "activation": {
            "mode": "activate_immediate"
        },
        "sender_id": "49f7cec5-fbb8-3425-9541-40a36ba03fb2",
        "transport_params": [
            {
                "interface_ip": "auto",
                "multicast_ip": "239.5.40.2",
                "rtp_enabled": True,
                "source_ip": "192.168.10.4",
                "destination_port": 20000
            }
        ],
        "transport_file": {
            "data": "v=0\r\no=- 1443716955 1443716955 IN IP4 192.168.10.4\r\ns=emsfp-a0-3f-b2_0-9-0\r\nt=0 0\r\nm=video 20000 RTP/AVP 100\r\nc=IN IP4 239.5.40.2/64\r\na=source-filter: incl IN IP4 239.5.40.2 192.168.10.4\r\na=rtpmap:100 smpte291/90000\r\na=fmtp:100 VPID_Code=133; \r\na=mediaclk:direct=0 rate=90000\r\na=ts-refclk:ptp=IEEE1588-2008:08-00-11-FF-FE-22-B6-CE:0\r\n",
            "type": "application/sdp"
        }
    }

}


disable_connections_single = {mapping: {"activation": {"mode": "activate_immediate"}, "master_enable": False} for
                              mapping in SingleMapping}
