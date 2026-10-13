
bool GetPppoeSid(long param_1,undefined2 *param_2,undefined2 *param_3)

{
  byte bVar1;
  byte *pbVar2;
  
  pbVar2 = *(byte **)(param_1 + 0x270);
  if (5 < DebugLevel) {
    printk(&DAT_00154718);
    printk(&DAT_00154730,*pbVar2 >> 4);
    printk(&DAT_00154740,*pbVar2 & 0xf);
    printk(&DAT_00154750,pbVar2[1]);
    printk(&DAT_00154760,*(ushort *)(pbVar2 + 2) >> 8 | *(ushort *)(pbVar2 + 2) << 8);
    printk(&DAT_00154770,*(ushort *)(pbVar2 + 4) >> 8 | *(ushort *)(pbVar2 + 4) << 8);
    printk(&DAT_00154780,*(ushort *)(pbVar2 + 6) >> 8 | *(ushort *)(pbVar2 + 6) << 8);
    printk(&DAT_00154790,*(ushort *)(pbVar2 + 8) >> 8 | *(ushort *)(pbVar2 + 8) << 8);
    printk(&DAT_001547a0);
  }
  *param_3 = *(undefined2 *)(pbVar2 + 6);
  bVar1 = *pbVar2;
  if (bVar1 == 0x11) {
    *param_2 = *(undefined2 *)(pbVar2 + 2);
  }
  return bVar1 != 0x11;
}

