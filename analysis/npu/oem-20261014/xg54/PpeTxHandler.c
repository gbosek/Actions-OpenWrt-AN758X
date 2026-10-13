
/* WARNING: Type propagation algorithm not settling */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 PpeTxHandler(long param_1,undefined8 *param_2,int param_3)

{
  long lVar1;
  byte bVar2;
  uint uVar3;
  uint uVar4;
  ushort uVar5;
  char cVar6;
  bool bVar7;
  char cVar8;
  int iVar9;
  uint *puVar10;
  undefined8 uVar11;
  short sVar12;
  uint uVar13;
  undefined4 uVar14;
  undefined1 auStack_68 [8];
  undefined1 auStack_60 [16];
  undefined1 auStack_50 [80];
  
  bVar2 = *(byte *)(param_1 + 0xd0) & 0x1f;
  if ((byte)(bVar2 - 0x18) < 2 || bVar2 == 0x16) {
    return 1;
  }
  if (((((_TCSUPPORT_PON_MVAL >> 10 & 1) == 0) || ((_DAT_0019651c >> 0x1d & 1) == 0)) ||
      ((*(uint *)(param_1 + 0xf0) >> 8 & 1) == 0)) || (*(char *)(param_1 + 0x154) != '\x01')) {
    uVar5 = *(ushort *)(param_1 + 0xce);
  }
  else {
    *(undefined2 *)(param_1 + 0xcc) = *(undefined2 *)(param_1 + 0x156);
    uVar5 = *(ushort *)(param_1 + 0x15a);
    *(uint *)(param_1 + 0xce) =
         *(uint *)(param_1 + 0xce) & 0xffe00000 |
         *(uint *)(param_1 + 0xce) & 0xffff | (*(byte *)(param_1 + 0x158) & 0x1f) << 0x10;
    *(ushort *)(param_1 + 0xce) = uVar5;
  }
  puVar10 = (uint *)getPpeEntryLocal(uVar5,auStack_50);
  if (puVar10 == (uint *)0x0) {
    return 0xffffffff;
  }
  if ((*puVar10 & 0x30000000) == 0) {
    return 0xffffffff;
  }
  iVar9 = ecnt_ppe_tx_hanlder_start_hook(puVar10,param_1,param_2,param_3);
  if (iVar9 != 0) {
    if (*(ushort *)(param_1 + 0xce) != hwnat_dbg_bindfail_idx) {
      return 1;
    }
    iVar9 = __printk_ratelimit("PpeTxHandler");
    if (iVar9 == 0) {
      return 1;
    }
    printk("%s,%d:return at tx handler start\n","PpeTxHandler",0x1a4d);
    return 1;
  }
  sVar12 = *(short *)(param_1 + 0xcc);
  if (2 < DebugLevel) {
    printk("PpeTxHandler FOE_MAGIC %x FOE_AI %x magic %x \n",sVar12,*(byte *)(param_1 + 0xd0) & 0x1f
           ,param_3);
    sVar12 = *(short *)(param_1 + 0xcc);
  }
  if ((sVar12 == 0) && ((*(byte *)(param_1 + 0xd0) & 0x1f) == 0)) {
    if (*(uint *)(param_1 + 0x180) == hwnat_dbg_bindfail_idx) {
      iVar9 = __printk_ratelimit("PpeTxHandler");
      if (iVar9 != 0) {
        printk("%s,%d, skb->foe is set to 0\n","PpeTxHandler",0x1a58);
      }
      goto LAB_00145430;
    }
LAB_0014545c:
    cVar8 = '\0';
  }
  else {
LAB_00145430:
    if (((((hwnat_fast_bind & 0xfffffffd) != 1) || ((*(byte *)(param_1 + 0xd0) & 0x1f) != 0xc)) &&
        ((hwnat_fast_bind != 2 || ((*(byte *)(param_1 + 0xd0) & 0x1f) != 0xd)))) ||
       ((*puVar10 & 0x30000000) == 0x20000000)) goto LAB_0014545c;
    cVar8 = ppe_tx_fast_bind(param_1,param_2,param_3);
  }
  iVar9 = ppe_check_start_to_bind(param_1,puVar10);
  if (iVar9 == 0) {
    uVar3 = (uint)(ushort)(*(short *)(param_1 + 0xcc) + 0x8d8c);
    uVar13 = (uint)(*(short *)(param_1 + 0xcc) == 0x7615);
    uVar4 = uVar13 | (uint)(0xfa63dff7fb >> ((ulong)uVar3 & 0x3f)) & 1;
    if (0x27 < uVar3) {
      uVar4 = uVar13;
    }
    if (uVar4 == 0) {
      return 1;
    }
    if ((*(byte *)(param_1 + 0xd0) & 0x1e) != 0x14) {
      return 1;
    }
    *(undefined4 *)(param_1 + 0xcc) = 0;
    uVar14 = 0;
    goto LAB_001457f8;
  }
  uVar11 = FUN_00139900();
  Hint_Prefetch(0x162858,2,0,1);
  do {
    uVar3 = hw_nat_lock;
    if (hw_nat_lock != 0) break;
    cVar6 = '\x01';
    bVar7 = (bool)ExclusiveMonitorPass(0x162858,0x10);
    if (bVar7) {
      hw_nat_lock = 1;
      cVar6 = ExclusiveMonitorsStatus();
    }
  } while (cVar6 != '\0');
  if (uVar3 != 0) {
    queued_spin_lock_slowpath();
  }
  iVar9 = PpeParseLayerInfo(param_1,param_2,param_3,puVar10);
  if (iVar9 == 0) {
    if (((_left_to_right_test_mode == 2) && (_update_vxlan_up_info_hook != (code *)0x0)) &&
       ((*(byte *)(foe_ext + (long)(int)(uint)uVar5 * 0x70 + 0x50) >> 3 & 1) != 0)) {
      (*_update_vxlan_up_info_hook)
                ((uint)*param_2 >> 8 & 0x1f,*(undefined2 *)((long)param_2 + 4),
                 DAT_00193d98 >> 8 | DAT_00193d98 << 8,0x193d8e);
      lVar1 = foe_ext + (long)(int)(uint)uVar5 * 0x70;
      *(byte *)(lVar1 + 0x50) = *(byte *)(lVar1 + 0x50) & 0xf7;
      hw_nat_lock = hw_nat_lock & 0xffffff00;
      daif = uVar11;
      return 1;
    }
    if (((DAT_00193ea8 & 3) == 0) || (param_3 - 0x7297U < 3)) {
      iVar9 = PpeFillInL2Info(param_1,puVar10);
      if (iVar9 == 0) {
        iVar9 = PpeFillInL3Info(param_1,puVar10);
        if (iVar9 == 0) {
          if ((int)DAT_00193e08 == 0) {
            if ((*puVar10 & 0xe000000) != 0x6000000) {
              FUN_0013a2b0(puVar10);
            }
          }
          else if (((int)DAT_00193e08 == 1) && (DAT_00193db5 == '/')) {
            *(short *)((long)puVar10 + 0x1e) = (short)DAT_00193e04;
          }
          goto LAB_00145680;
        }
        hw_nat_lock = hw_nat_lock & 0xffffff00;
        daif = uVar11;
        if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
           (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
          printk("%s,%d:fill L3 info fail\n","PpeTxHandler",0x1aa7);
        }
      }
      else {
        hw_nat_lock = hw_nat_lock & 0xffffff00;
        daif = uVar11;
        if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
           (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
          printk("%s,%d:fill L2 info fail\n","PpeTxHandler",0x1a9e);
        }
      }
    }
    else {
      iVar9 = PpeFillInL2Info_InTunnel(param_1,puVar10);
      if (iVar9 == 0) {
        iVar9 = PpeFillInL3Info_InTunnel(param_1,puVar10);
        if (iVar9 == 0) {
          if (DAT_00193ea0 == 0) {
            FUN_0013a324(puVar10);
          }
LAB_00145680:
          iVar9 = PpeSetForcePortInfo(param_1,puVar10,param_2,param_3);
          if (iVar9 == 0) {
            iVar9 = PpeSetExtIfNum(param_1,puVar10,param_3);
            if (iVar9 == 0) {
              ppeUpdateAcntInfo(puVar10,param_1,param_3,param_2);
              if (check_gemport != 0) {
                *(uint *)(foe_ext + (ulong)*(ushort *)(param_1 + 0xce) * 0x70 + 0x54) =
                     (uint)*(ushort *)(param_1 + 0xee);
              }
              iVar9 = isValidPpeEntry(param_1,puVar10);
              if (iVar9 != 0) {
                PpeSetEntryBind(param_1,puVar10);
                if ((_TCSUPPORT_DP_MVAL >> 4 & 1) != 0) {
                  PpeL2luKeySetStatusBind(*(undefined2 *)(param_1 + 0xce));
                }
                if ((hwnat_fast_bind == 3 && cVar8 == '\x01') &&
                   ((*(ushort *)(param_1 + 0xd0) >> 5 & 0x1f) != 2)) {
                  ppeSetDualEntryInfo(uVar5,auStack_68,auStack_60);
                  ppeSetDualEntry(uVar5,puVar10,auStack_68,auStack_60);
                }
                else {
                  iVar9 = GET_HIR();
                  if (((iVar9 == 10) ||
                      ((iVar9 = GET_HIR(), iVar9 == 0xc || (iVar9 = GET_HIR(), iVar9 == 0xe)))) &&
                     (uVar5 < 0x4000)) {
                    setPpeEntry(uVar5,puVar10);
                  }
                }
                if ((_xpon_igmp_learn_flow_hook == (code *)0x0) ||
                   (iVar9 = ppe_is_multicast_entry(puVar10), iVar9 == 0)) {
                  ecnt_multicast_hwnat_learn_flow(param_1);
                }
                else {
                  (*_xpon_igmp_learn_flow_hook)(param_1);
                }
                hw_nat_lock = hw_nat_lock & 0xffffff00;
                daif = uVar11;
                ecnt_ppe_tx_hanlder_end_hook(puVar10,param_1,param_2,param_3);
                if (DebugLevel < 1) {
                  return 1;
                }
                FoeDumpEntry(*(undefined2 *)(param_1 + 0xce));
                return 1;
              }
              hw_nat_lock = hw_nat_lock & 0xffffff00;
              daif = uVar11;
              if (0 < DebugLevel) {
                printk("Invalid PPE entry, not bind !!!, FOE index = %d\n",uVar5);
              }
            }
            else {
              hw_nat_lock = hw_nat_lock & 0xffffff00;
              daif = uVar11;
              if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
                 (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
                printk("%s,%d:set ext if num fail\n","PpeTxHandler",0x1ac6);
              }
            }
          }
          else {
            hw_nat_lock = hw_nat_lock & 0xffffff00;
            daif = uVar11;
            if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
               (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
              printk("%s,%d:set force port fail\n","PpeTxHandler",0x1abc);
            }
          }
        }
        else {
          hw_nat_lock = hw_nat_lock & 0xffffff00;
          daif = uVar11;
          if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
             (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
            printk("%s,%d:fill L3 info fail\n","PpeTxHandler",0x1a8b);
          }
        }
      }
      else {
        hw_nat_lock = hw_nat_lock & 0xffffff00;
        daif = uVar11;
        if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
           (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
          printk("%s,%d:fill L2 info fail\n","PpeTxHandler",0x1a82);
        }
      }
    }
  }
  else {
    hw_nat_lock = hw_nat_lock & 0xffffff00;
    daif = uVar11;
    if ((*(ushort *)(param_1 + 0xce) == hwnat_dbg_bindfail_idx) &&
       (iVar9 = __printk_ratelimit("PpeTxHandler"), iVar9 != 0)) {
      printk("%s,%d:parse layer info fail\n","PpeTxHandler",0x1a69);
    }
  }
  uVar14 = 1;
  *(undefined4 *)(param_1 + 0xcc) = 0;
LAB_001457f8:
  *(undefined2 *)(param_1 + 0xd0) = 0;
  *(undefined1 *)(param_1 + 0xd2) = 0;
  return uVar14;
}

