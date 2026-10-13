
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */
/* WARNING: Restarted to delay deadcode elimination for space: ram */

void PpeTxHandler(long param_1,undefined8 param_2,ulong param_3)

{
  ushort uVar1;
  bool bVar2;
  char cVar3;
  char cVar4;
  undefined1 uVar5;
  ushort uVar6;
  int iVar7;
  int iVar8;
  uint uVar9;
  uint *puVar10;
  undefined8 uVar11;
  undefined8 uVar12;
  long lVar13;
  long lVar14;
  undefined8 *puVar15;
  ulong uVar16;
  long lStack_e0;
  undefined1 auStack_d0 [8];
  undefined1 auStack_c8 [16];
  undefined1 auStack_b8 [80];
  long local_68;
  
  lVar14 = sp_el0;
  local_68 = *(long *)(lVar14 + 0x3f0);
  if (hwnat_enable_status == 0) {
LAB_0015b408:
    uVar11 = 0xffffffff;
    goto LAB_0015b40c;
  }
  if ((0x3400000UL >> (*(byte *)(param_1 + 0x131) & 0x1f) & 1) != 0) goto LAB_0015b510;
  if (((((_TCSUPPORT_PON_MVAL >> 10 & 1) == 0) || ((_DAT_001a25a4 >> 0x1d & 1) == 0)) ||
      ((*(uint *)(param_1 + 0xbc) >> 8 & 1) == 0)) || (*(char *)(param_1 + 0x118) != '\x01')) {
    uVar1 = *(ushort *)(param_1 + 0x12f);
  }
  else {
    uVar1 = *(ushort *)(param_1 + 0x11e);
    *(undefined2 *)(param_1 + 0x12d) = *(undefined2 *)(param_1 + 0x11a);
    *(uint *)(param_1 + 0x12f) =
         *(uint *)(param_1 + 0x12f) & 0xffe00000 | (*(byte *)(param_1 + 0x11c) & 0x1f) << 0x10 |
         (uint)uVar1;
  }
  puVar10 = (uint *)getPpeEntryLocal(uVar1,auStack_b8,param_3,lVar14,0);
  if ((puVar10 == (uint *)0x0) || ((*puVar10 & 0x30000000) == 0)) goto LAB_0015b408;
  iVar8 = (int)param_3;
  if ((_TCSUPPORT_SOC_MVAL & 0x80000) == 0 || iVar8 != 0x72a1) {
    iVar7 = ecnt_ppe_tx_hanlder_start_hook(puVar10,param_1,param_2,param_3 & 0xffffffff);
    if (iVar7 == 0) {
      if (2 < DebugLevel) {
        _printk("PpeTxHandler FOE_MAGIC %x FOE_AI %x magic %x \n",*(undefined2 *)(param_1 + 0x12d),
                *(byte *)(param_1 + 0x131) & 0x1f,param_3 & 0xffffffff);
      }
      if ((*(short *)(param_1 + 0x12d) == 0) && ((*(byte *)(param_1 + 0x131) & 0x1f) == 0)) {
        if (*(uint *)(param_1 + 0x144) == hwnat_dbg_bindfail_idx) {
          iVar7 = __printk_ratelimit("PpeTxHandler");
          if (iVar7 != 0) {
            _printk("%s,%d, skb->foe is set to 0\n","PpeTxHandler",0x2441);
          }
          goto LAB_0015b4a0;
        }
LAB_0015b380:
        cVar4 = '\0';
      }
      else {
LAB_0015b4a0:
        if ((hwnat_fast_bind & 0xfffffffd) == 1) {
          if ((*(byte *)(param_1 + 0x131) & 0x1f) == 0xc) goto LAB_0015b4cc;
          goto LAB_0015b380;
        }
        if ((hwnat_fast_bind != 2) || ((*(byte *)(param_1 + 0x131) & 0x1f) != 0xd))
        goto LAB_0015b380;
LAB_0015b4cc:
        if ((*puVar10 & 0x30000000) == 0x20000000) goto LAB_0015b380;
        cVar4 = ppe_tx_fast_bind(param_1,param_2,param_3 & 0xffffffff);
      }
      cVar3 = cacel_hwnat_accelerate(puVar10);
      if (cVar3 != '\0') goto LAB_0015b5b8;
      uVar11 = ppe_check_start_to_bind(param_1,puVar10);
      if ((int)uVar11 == 0) {
        uVar9 = (uint)*(ushort *)(param_1 + 0x12d);
        if (*(ushort *)(param_1 + 0x12d) < 0x72a4) {
          if ((0x7273 < uVar9) && ((0xdffb63dff7fbU >> ((ulong)(uVar9 - 0x7274) & 0x3f) & 1) != 0))
          {
LAB_0015b3dc:
            if ((*(byte *)(param_1 + 0x131) & 0x1e) == 0x14) {
              *(undefined4 *)(param_1 + 0x12d) = 0;
              *(undefined2 *)(param_1 + 0x131) = 0;
              *(undefined1 *)(param_1 + 0x133) = 0;
              goto LAB_0015b40c;
            }
          }
        }
        else if (uVar9 == 0x7615) goto LAB_0015b3dc;
        goto LAB_0015b510;
      }
      uVar11 = daif;
      uVar16 = daif;
      daif = uVar16 | 0xc0;
      Hint_Prefetch(0x16e610,2,0,1);
      do {
        uVar9 = hw_nat_lock;
        if (hw_nat_lock != 0) break;
        cVar3 = '\x01';
        bVar2 = (bool)ExclusiveMonitorPass(0x16e610,0x10);
        if (bVar2) {
          hw_nat_lock = 1;
          cVar3 = ExclusiveMonitorsStatus();
        }
      } while (cVar3 != '\0');
      if (uVar9 != 0) {
        queued_spin_lock_slowpath(&hw_nat_lock);
      }
      iVar7 = PpeParseLayerInfo(param_1,param_2,param_3 & 0xffffffff,puVar10);
      if (iVar7 == 0) {
        if (((DAT_0019fd28 & 3) == 0) || (iVar8 - 0x7297U < 3)) {
          iVar7 = PpeCheckSRv6(param_1,puVar10);
          if (iVar7 == 0) {
            if (DAT_0019fc88 == 5) {
              uVar9 = *puVar10;
              if ((uVar9 & 0xe000000) != 0) goto LAB_0015b690;
            }
            else if ((DAT_0019fc88 != 0) || (uVar9 = *puVar10, (uVar9 & 0xe000000) != 0xa000000)) {
LAB_0015b690:
              iVar7 = PpeCheckSoe(param_1);
              if (iVar7 == 0) {
                iVar7 = PpeFillInL2Info(param_1,puVar10);
                if (iVar7 == 0) {
                  iVar7 = PpeFillInL3Info(param_1,puVar10);
                  if (iVar7 == 0) {
                    iVar7 = PpeFillInL4Info(param_1,puVar10);
                    if (iVar7 == 0) goto LAB_0015b6ac;
                    hw_nat_lock = hw_nat_lock & 0xffffff00;
                    daif = uVar11;
                    if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                       (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
                      _printk("%s,%d:fill L4 info fail\n","PpeTxHandler",0x24ba);
                    }
                  }
                  else {
                    hw_nat_lock = hw_nat_lock & 0xffffff00;
                    daif = uVar11;
                    if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                       (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
                      _printk("%s,%d:fill L3 info fail\n","PpeTxHandler",0x24b1);
                    }
                  }
                }
                else {
                  hw_nat_lock = hw_nat_lock & 0xffffff00;
                  daif = uVar11;
                  if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                     (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
                    _printk("%s,%d:fill L2 info fail\n","PpeTxHandler",0x24a8);
                  }
                }
              }
              else {
                iVar7 = PpeFillSoeInfo(param_1);
                if (iVar7 == 0) goto LAB_0015b6ac;
                hw_nat_lock = hw_nat_lock & 0xffffff00;
                daif = uVar11;
                if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                   (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
                  _printk("%s,%d:fill Soe info fail\n","PpeTxHandler",0x249e);
                }
              }
              goto LAB_0015b5b8;
            }
            if ((uVar9 & 0x30000000) == 0x20000000) {
LAB_0015bcfc:
              hw_nat_lock = hw_nat_lock & 0xffffff00;
              daif = uVar11;
              if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                 (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
                _printk("%s,%d:PpeTunnelMapFillEntry fail\n","PpeTxHandler",0x2496);
              }
              goto LAB_0015b510;
            }
            PpeClearEntryInfo(puVar10);
            if ((DAT_0019fc88 == 5) && ((*puVar10 & 0xe000000) == 0)) {
              FoeSetEntryMac(&DAT_0019fc0e,puVar10 + 0xe,(long)puVar10 + 0x3e);
              uVar12 = GetMacAddr();
              FoeSetEntryMac(uVar12,puVar10 + 0xc,(long)puVar10 + 0x36);
              if (DAT_0019fc40._6_1_ == '\x06') {
                *(ushort *)((long)puVar10 + 0x1e) = DAT_0019fc68 >> 8 | DAT_0019fc68 << 8;
                *(ushort *)(puVar10 + 7) = DAT_0019fc6a >> 8 | DAT_0019fc6a << 8;
              }
              else {
                if (DAT_0019fc40._6_1_ != '\x11') {
                  if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                     (iVar8 = __printk_ratelimit("PpeTunnelMapFillEntry"), iVar8 != 0)) {
                    _printk("%s,%d:protocol %d,MAP-T up only suooprt TCP/UDP\n",
                            "PpeTunnelMapFillEntry",0x2227,DAT_0019fc40._6_1_);
                  }
                  goto LAB_0015bcfc;
                }
                *(ushort *)((long)puVar10 + 0x1e) = DAT_0019fc7c >> 8 | DAT_0019fc7c << 8;
                *(ushort *)(puVar10 + 7) = DAT_0019fc7e >> 8 | DAT_0019fc7e << 8;
              }
            }
            else {
              puVar10[0xf] = puVar10[0xf] & 0xffe00000 | puVar10[0xf] & 0xffff | 0xf0000;
              uVar12 = GetMacAddr();
              FoeSetEntryMac(uVar12,puVar10 + 0xd,(long)puVar10 + 0x3a);
              if (DAT_0019fc35 != '\x06' && DAT_0019fc35 != '\x11') {
                if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                   (iVar8 = __printk_ratelimit("PpeTunnelMapFillEntry"), iVar8 != 0)) {
                  _printk("%s,%d:protocol %d,MAP-T down only suooprt TCP/UDP\n",
                          "PpeTunnelMapFillEntry",0x2231,DAT_0019fc35);
                }
                goto LAB_0015bcfc;
              }
            }
            if ((DAT_0019fc88 == 5) && ((*puVar10 & 0xe000000) == 0)) {
              uVar9 = PpeGetTunnel_table_index(0,4);
              if (uVar9 == 0xffffffff) {
                if (1 < DebugLevel) {
                  _printk("there is none tunnel table use for MAP DSLITE tunnel\n");
                }
              }
              else {
                lStack_e0 = (long)(int)uVar9;
                if (((*(ulong *)(TUNNEL_SWTABLE + lStack_e0 * 0x58 + 0x40) >> 0x21 & 1) == 0) &&
                   (DAT_0015fa54 <= DAT_001a0188)) {
                  if (1 < DebugLevel) {
                    _printk("mapt goes offload\n");
                  }
                }
                else {
                  if (1 < DebugLevel) {
                    _printk("mapt goes tunnel\n");
                  }
                  DAT_0019fd28 = (uVar9 & 0x3f) << 0x11 | 0x10060 | DAT_0019fd28 & 0xff80000f;
                  if ((*(ulong *)(TUNNEL_SWTABLE + lStack_e0 * 0x58 + 0x40) >> 0x21 & 1) == 0) {
                    if (uVar9 < 0x40) {
                      FUN_0014f784(uVar9);
                    }
LAB_0015b87c:
                    PpeSetTunnel_table_ToHW(uVar9);
                    DAT_001a0188 = DAT_001a0188 + 1;
                    TUNNEL_SWTABLE[lStack_e0 * 0x58 + 0x44] =
                         TUNNEL_SWTABLE[lStack_e0 * 0x58 + 0x44] | 6;
                  }
LAB_0015b8b0:
                  ppe_add_session_to_tunnel_list(uVar9,*(undefined2 *)(param_1 + 0x12f));
                }
              }
            }
            else {
              uVar9 = PpeGetTunnel_table_index(0,5);
              if (uVar9 == 0xffffffff) {
                if (1 < DebugLevel) {
                  _printk("there is none tunnel table use for MAP 6RD tunnel\n");
                }
              }
              else {
                lStack_e0 = (long)(int)uVar9;
                if (((*(ulong *)(TUNNEL_SWTABLE + lStack_e0 * 0x58 + 0x40) >> 0x21 & 1) != 0) ||
                   (DAT_001a0188 < DAT_0015fa54)) {
                  if (1 < DebugLevel) {
                    _printk("mapt down goes tunnel\n");
                  }
                  DAT_0019fd28 = (uVar9 & 0x3f) << 0x11 | 0x10060 | DAT_0019fd28 & 0xff80000f;
                  if ((*(ulong *)(TUNNEL_SWTABLE + lStack_e0 * 0x58 + 0x40) >> 0x21 & 1) == 0) {
                    if (uVar9 < 0x40) {
                      FUN_0014d7f8(uVar9);
                    }
                    goto LAB_0015b87c;
                  }
                  goto LAB_0015b8b0;
                }
                if (1 < DebugLevel) {
                  _printk("mapt down goes offload\n");
                }
              }
            }
          }
          else {
            iVar7 = PpeTunnelSRv6FillEntry(param_1,puVar10);
            if (iVar7 != 0) {
              hw_nat_lock = hw_nat_lock & 0xffffff00;
              daif = uVar11;
              if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
                 (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
                _printk("%s,%d:PpeTunnelSRv6FillEntry fail\n","PpeTxHandler",0x248e);
              }
              goto LAB_0015b510;
            }
          }
LAB_0015b6ac:
          iVar7 = PpeSetForcePortInfo(param_1,puVar10,param_2,param_3 & 0xffffffff);
          if (iVar7 == 0) {
            iVar7 = PpeSetExtIfNum(param_1,puVar10,param_3 & 0xffffffff);
            if (iVar7 == 0) {
              ppeUpdateAcntInfo(puVar10,param_1,param_3 & 0xffffffff,param_2);
              if (check_gemport != 0) {
                *(uint *)(foe_ext + (ulong)*(ushort *)(param_1 + 0x12f) * 0xa8 + 0x5c) =
                     (uint)*(ushort *)(param_1 + 0xba);
              }
              uVar9 = DAT_0019fd28 >> 0x10 & 1;
              if (DAT_0019fc88 == 5) {
                if ((*puVar10 & 0xe000000) != 0) goto LAB_0015baec;
                if (uVar9 == 0) {
                  iVar7 = FUN_0014cb70(param_1,0);
                  if (iVar7 != 0) goto LAB_0015bcdc;
                  puVar10[4] = puVar10[4] & 0xfffffdff;
                  if (DAT_001a01c0 + 1 == DAT_0015fa50) {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x43;
                    DAT_001a01c0 = 0;
                  }
                  else {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x43;
                    DAT_001a01c0 = DAT_001a01c0 + 1;
                  }
                }
                else {
                  puVar10[4] = puVar10[4] & 0xfffffdff;
                  if (DAT_001a01c0 + 1 == DAT_0015fa50) {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x41;
                    DAT_001a01c0 = 0;
                  }
                  else {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x41;
                    DAT_001a01c0 = DAT_001a01c0 + 1;
                  }
                }
                *(undefined1 *)((long)puVar10 + 0x2b) = uVar5;
                *(ushort *)(puVar10 + 4) = (ushort)puVar10[4] & 0xfe00 | uVar6 | 0xc0;
LAB_0015bfec:
                DAT_0019fc1e = 0;
                DAT_0019fc20 = 0;
LAB_0015baec:
                iVar7 = PpeSRv6Handle(param_1,puVar10);
                if (iVar7 == 0) {
                  iVar7 = isValidPpeEntry(param_1,puVar10);
                  if (iVar7 != 0) {
                    PpeSetEntryBind(param_1,puVar10);
                    lVar14 = foe_ext;
                    uVar16 = 0xa8;
                    *(undefined8 *)(foe_ext + (ulong)*(ushort *)(param_1 + 0x12f) * 0xa8 + 0x20) =
                         *(undefined8 *)(param_1 + 0x10);
                    if (iVar8 == 0x729a) {
                      uVar5 = skb_get_xfi_vlan_port(param_1);
                      *(undefined1 *)
                       (lVar14 + (ulong)*(ushort *)(param_1 + 0x12f) * (uVar16 & 0xffffffff) + 99) =
                           uVar5;
                    }
                    lVar13 = lVar14 + (ulong)*(ushort *)(param_1 + 0x12f) * 0xa8;
                    *(undefined8 *)(lVar13 + 0x94) = 0;
                    *(undefined8 *)(lVar13 + 0x9c) = 0;
                    puVar15 = *(undefined8 **)(param_1 + 0x148);
                    if (puVar15 != (undefined8 *)0x0) {
                      uVar12 = puVar15[1];
                      lVar14 = lVar14 + (ulong)*(ushort *)(param_1 + 0x12f) * 0xa8;
                      *(undefined8 *)(lVar14 + 0x94) = *puVar15;
                      *(undefined8 *)(lVar14 + 0x9c) = uVar12;
                    }
                    hwnat_mirror_setting(param_1,puVar10,param_2,param_3 & 0xffffffff);
                    if ((_TCSUPPORT_DP_MVAL >> 4 & 1) != 0) {
                      PpeL2luKeySetStatusBind(*(undefined2 *)(param_1 + 0x12f));
                    }
                    if ((hwnat_fast_bind == 3 && cVar4 == '\x01') &&
                       ((*(ushort *)(param_1 + 0x131) >> 5 & 0x1f) != 2)) {
                      ppeSetDualEntryInfo(uVar1,auStack_d0,auStack_c8);
                      ppeSetDualEntry(uVar1,puVar10,auStack_d0,auStack_c8);
                    }
                    else {
                      iVar8 = GET_HIR();
                      if ((((iVar8 == 10) ||
                           (((iVar8 = GET_HIR(), iVar8 == 0xc || (iVar8 = GET_HIR(), iVar8 == 0xe))
                            || (iVar8 = GET_HIR(), iVar8 == 0xf)))) ||
                          (iVar8 = GET_HIR(), iVar8 == 0x10)) && (uVar1 < hwnat_dram_idx_base)) {
                        setPpeEntry(uVar1,puVar10);
                      }
                    }
                    if (((_xpon_igmp_learn_flow_hook == (code *)0x0) ||
                        (iVar8 = ppe_is_multicast_entry(puVar10), iVar8 == 0)) ||
                       ((*puVar10 & 0x30000000) != 0x20000000)) {
                      ecnt_multicast_hwnat_learn_flow(param_1);
                    }
                    else {
                      (*_xpon_igmp_learn_flow_hook)(param_1);
                    }
                    if ((*(ushort *)(param_1 + 0x131) >> 5 & 0x1f) == 2) {
                      FUN_0014d37c(param_1);
                    }
                    hw_nat_lock = hw_nat_lock & 0xffffff00;
                    daif = uVar11;
                    ecnt_ppe_tx_hanlder_end_hook(puVar10,param_1,param_2,param_3 & 0xffffffff);
                    if (0 < DebugLevel) {
                      FoeDumpEntry(*(undefined2 *)(param_1 + 0x12f));
                    }
                    goto LAB_0015b510;
                  }
                  hw_nat_lock = hw_nat_lock & 0xffffff00;
                  daif = uVar11;
                  if (0 < DebugLevel) {
                    _printk("Invalid PPE entry, not bind !!!, FOE index = %d\n",uVar1);
                  }
                  goto LAB_0015b5b8;
                }
              }
              else {
                if ((DAT_0019fc88 != 0) || ((*puVar10 & 0xe000000) != 0xa000000)) goto LAB_0015baec;
                if (uVar9 != 0) {
                  puVar10[0xb] = puVar10[0xb] & 0xfffffdff;
                  if (DAT_001a01c0 + 1 == DAT_0015fa50) {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x42;
                    DAT_001a01c0 = 0;
                  }
                  else {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x42;
                    DAT_001a01c0 = DAT_001a01c0 + 1;
                  }
LAB_0015c19c:
                  *(undefined1 *)((long)puVar10 + 0x2b) = uVar5;
                  *(ushort *)(puVar10 + 0xb) = (ushort)puVar10[0xb] & 0xfe00 | uVar6 | 0xc0;
                  if (DAT_0019fc35 == '\x06') {
                    *(ushort *)((long)puVar10 + 0x32) = DAT_0019fc6a >> 8 | DAT_0019fc6a << 8;
                  }
                  else if (DAT_0019fc35 == '\x11') {
                    *(ushort *)((long)puVar10 + 0x32) = DAT_0019fc7e >> 8 | DAT_0019fc7e << 8;
                  }
                  goto LAB_0015bfec;
                }
                iVar7 = FUN_0014cb70(param_1,1);
                if (iVar7 == 0) {
                  puVar10[0xb] = puVar10[0xb] & 0xfffffdff;
                  if (DAT_0015fa50 == DAT_001a01c0 + 1) {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x44;
                    DAT_001a01c0 = 0;
                  }
                  else {
                    uVar6 = (ushort)*(undefined4 *)(&DAT_0015fa58 + (long)DAT_001a01c0 * 4) & 0x1f;
                    uVar5 = 0x44;
                    DAT_001a01c0 = DAT_001a01c0 + 1;
                  }
                  goto LAB_0015c19c;
                }
              }
LAB_0015bcdc:
              hw_nat_lock = hw_nat_lock & 0xffffff00;
              daif = uVar11;
              goto LAB_0015b510;
            }
            hw_nat_lock = hw_nat_lock & 0xffffff00;
            daif = uVar11;
            if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
               (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
              _printk("%s,%d:set ext if num fail\n","PpeTxHandler",0x24cf);
            }
          }
          else {
            hw_nat_lock = hw_nat_lock & 0xffffff00;
            daif = uVar11;
            if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
               (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
              _printk("%s,%d:set force port fail\n","PpeTxHandler",0x24c5);
            }
          }
        }
        else {
          iVar7 = PpeFillInL2Info_InTunnel(param_1,puVar10);
          if (iVar7 == 0) {
            iVar7 = PpeFillInL3Info_InTunnel(param_1,puVar10);
            if (iVar7 == 0) {
              if (DAT_0019fd20 == 0) {
                if (DAT_0019fcd0._1_1_ == '\x06') {
                  *(ushort *)((long)puVar10 + 0x1e) = DAT_0019fd04 >> 8 | DAT_0019fd04 << 8;
                  uVar6 = DAT_0019fd06;
                  *puVar10 = *puVar10 & 0xbfffffff;
                  *(ushort *)(puVar10 + 7) = uVar6 >> 8 | uVar6 << 8;
                }
                else if (DAT_0019fcd0._1_1_ == '\x11') {
                  *(ushort *)((long)puVar10 + 0x1e) = DAT_0019fd18 >> 8 | DAT_0019fd18 << 8;
                  uVar6 = DAT_0019fd1a;
                  *puVar10 = *puVar10 | 0x40000000;
                  *(ushort *)(puVar10 + 7) = uVar6 >> 8 | uVar6 << 8;
                }
              }
              goto LAB_0015b6ac;
            }
            hw_nat_lock = hw_nat_lock & 0xffffff00;
            daif = uVar11;
            if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
               (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
              _printk("%s,%d:fill L3 info fail\n","PpeTxHandler",0x247b);
            }
          }
          else {
            hw_nat_lock = hw_nat_lock & 0xffffff00;
            daif = uVar11;
            if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
               (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
              _printk("%s,%d:fill L2 info fail\n","PpeTxHandler",0x2472);
            }
          }
        }
      }
      else {
        hw_nat_lock = hw_nat_lock & 0xffffff00;
        daif = uVar11;
        if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
           (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
          _printk("%s,%d:parse layer info fail\n","PpeTxHandler",0x2459);
        }
      }
LAB_0015b5b8:
      *(undefined4 *)(param_1 + 0x12d) = 0;
      *(undefined2 *)(param_1 + 0x131) = 0;
      *(undefined1 *)(param_1 + 0x133) = 0;
    }
    else if ((*(ushort *)(param_1 + 0x12f) == hwnat_dbg_bindfail_idx) &&
            (iVar8 = __printk_ratelimit("PpeTxHandler"), iVar8 != 0)) {
      _printk("%s,%d:return at tx handler start\n","PpeTxHandler",0x2436);
    }
  }
LAB_0015b510:
  uVar11 = 1;
LAB_0015b40c:
  lVar13 = sp_el0;
  lVar14 = local_68 - *(long *)(lVar13 + 0x3f0);
  if (lVar14 == 0) {
    return;
  }
                    /* WARNING: Subroutine does not return */
  __stack_chk_fail(uVar11,lVar13,0,lVar14);
}

